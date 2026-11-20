import gc
import math
import os
import re
import time
from functools import lru_cache

import torch
from peft import PeftModel
from spellchecker import SpellChecker
from transformers import AutoModelForCausalLM, AutoTokenizer

BASE_MODEL_NAME = "facebook/opt-125m"
ADAPTER_DIR = "./models/opt-125m-lora-adapter"

PUNCTUATION_TOKENS = (".", ",", "?", "!")

PROFANITY_BLOCKLIST = {
    "damn", "hell", "shit", "fuck", "bitch", "bastard", "asshole", "crap", "idiot"
}

VARIANT_METADATA = {
    "lora_int8": {
        "label": "LoRA Fine-Tuned OPT-125M (INT8 Quantized)",
        "size_label": "~271.7 MB (INT8 in-memory)",
    },
    "lora_fp32": {
        "label": "LoRA Fine-Tuned OPT-125M (FP32)",
        "size_label": "500.8 MB (FP32)",
    },
    "base": {
        "label": "Base Pre-trained OPT-125M (Zero-Shot FP32)",
        "size_label": "500.8 MB (FP32)",
    },
}


@lru_cache(maxsize=1)
def english_spellchecker():
    return SpellChecker(language="en", distance=1)


def spelling_candidates(word, limit=5):
    """Suggest edits for unknown English words without changing user text."""
    if not word.isascii() or not word.isalpha() or not 3 <= len(word) <= 24:
        return []
    spell = english_spellchecker()
    lower = word.lower()
    if spell.known([lower]):
        return []
    candidates = spell.candidates(lower) or set()
    ranked = sorted(
        (w for w in candidates if w != lower and w not in PROFANITY_BLOCKLIST),
        key=lambda w: (-spell.word_usage_frequency(w), w),
    )[:limit]
    if word.isupper():
        return [w.upper() for w in ranked]
    if word.istitle():
        return [w.capitalize() for w in ranked]
    return ranked


class OPTKeyboardPredictor:
    def __init__(self, model, tokenizer, device: str = "cpu", variant: str = "lora_int8"):
        self.model = model.to(device)
        self.model.eval()
        self.tokenizer = tokenizer
        self.device = device
        self.variant = variant
        self.variant_info = VARIANT_METADATA.get(variant, {})
        self.user_freq_cache = {}
        self._last_log_probs_cache = (None, None)
        self._build_vocabulary_index()

    @classmethod
    def from_variant(cls, variant: str = "lora_int8", device: str = "cpu"):
        try:
            tokenizer = AutoTokenizer.from_pretrained(ADAPTER_DIR)
        except Exception:
            tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_NAME)

        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        # Explicitly force Float32 on CPU so INT8 dynamic quantization never hits a Half/Float mismatch
        base_model = AutoModelForCausalLM.from_pretrained(
            BASE_MODEL_NAME,
            torch_dtype=torch.float32,
        ).float().cpu()

        if variant == "base":
            model = base_model
        elif variant in ("lora_fp32", "lora_int8"):
            if not os.path.isdir(ADAPTER_DIR):
                raise FileNotFoundError(
                    f"LoRA adapter directory not found at '{ADAPTER_DIR}'. "
                    "Ensure 'models/opt-125m-lora-adapter/' is uploaded to your repository."
                )
            peft_model = PeftModel.from_pretrained(base_model, ADAPTER_DIR)
            merged_model = peft_model.merge_and_unload().float().cpu()

            del peft_model
            del base_model
            gc.collect()

            if variant == "lora_fp32":
                model = merged_model
            else:
                device = "cpu"
                engines = torch.backends.quantized.supported_engines
                if "fbgemm" in engines:
                    torch.backends.quantized.engine = "fbgemm"
                elif "qnnpack" in engines:
                    torch.backends.quantized.engine = "qnnpack"

                try:
                    q_model = torch.ao.quantization.quantize_dynamic(
                        merged_model,
                        {torch.nn.Linear},
                        dtype=torch.qint8,
                    )
                    q_model.eval()
                    # Verify CPU quantized kernel works in this container
                    with torch.no_grad():
                        q_model(torch.tensor([[2]], dtype=torch.long))
                    model = q_model
                    del merged_model
                    gc.collect()
                except Exception:
                    # Graceful fallback to Float32 merged model if container lacks qint8 CPU ops
                    model = merged_model
        else:
            raise ValueError(f"Unknown variant: {variant}")

        return cls(model=model, tokenizer=tokenizer, device=device, variant=variant)

    def _build_vocabulary_index(self):
        vocab = self.tokenizer.get_vocab()
        self.whole_word_ids = []
        self.punct_ids = []
        self.id_to_word = {}
        self.word_to_ids = {}

        for token_str, token_id in vocab.items():
            if token_str.startswith("Ġ"):
                clean_word = token_str[1:]
                if (
                    clean_word.isalpha()
                    and len(clean_word) >= 1
                    and clean_word.lower() not in PROFANITY_BLOCKLIST
                ):
                    self.whole_word_ids.append(token_id)
                    self.id_to_word[token_id] = clean_word
                    lower_w = clean_word.lower()
                    self.word_to_ids.setdefault(lower_w, []).append(token_id)

        for p_tok in PUNCTUATION_TOKENS:
            tok_id = vocab.get(p_tok)
            if tok_id is not None:
                self.punct_ids.append(tok_id)
                self.id_to_word[tok_id] = p_tok

        self.whole_word_tensor = torch.tensor(self.whole_word_ids, dtype=torch.long)
        self.punct_tensor = torch.tensor(self.punct_ids, dtype=torch.long)

    def update_user_cache(self, text: str):
        words = [w.strip(".,!?;:'\"") for w in text.split()]
        for w in words:
            if w.isalpha() and len(w) > 1:
                key = w.lower()
                self.user_freq_cache[key] = self.user_freq_cache.get(key, 0) + 1

    def _rank_word_candidates(self, word: str, prefix: str):
        """Re-rank spelling candidates using batched OPT-125M contextual log-probabilities."""
        candidates = spelling_candidates(word)
        if not candidates:
            return []

        has_prefix = bool(prefix.strip())
        base_left = (
            self.tokenizer.encode(prefix.rstrip(), add_special_tokens=False)
            if has_prefix
            else []
        )
        bos = (
            self.tokenizer.bos_token_id
            if self.tokenizer.bos_token_id is not None
            else self.tokenizer.eos_token_id
        )
        pad_id = (
            self.tokenizer.pad_token_id
            if self.tokenizer.pad_token_id is not None
            else (bos if bos is not None else 0)
        )

        valid_candidates = []
        batch_seqs = []
        batch_spans = []

        for candidate in candidates:
            suffix = self.tokenizer.encode(
                " " + candidate if has_prefix else candidate,
                add_special_tokens=False,
            )
            if not suffix:
                continue
            left = base_left[-max(1, 127 - len(suffix)):] if base_left else [bos]
            seq = left + suffix
            valid_candidates.append(candidate)
            batch_seqs.append(seq)
            batch_spans.append((len(left), suffix))

        if not batch_seqs:
            return []

        max_len = max(len(seq) for seq in batch_seqs)
        padded_ids = [seq + [pad_id] * (max_len - len(seq)) for seq in batch_seqs]
        attn_masks = [[1] * len(seq) + [0] * (max_len - len(seq)) for seq in batch_seqs]

        input_ids = torch.tensor(padded_ids, dtype=torch.long, device=self.device)
        attention_mask = torch.tensor(attn_masks, dtype=torch.long, device=self.device)

        with torch.no_grad():
            logits = self.model(
                input_ids=input_ids,
                attention_mask=attention_mask,
            ).logits.float()
            scores = torch.log_softmax(logits, dim=-1)

        scored = []
        for idx, (candidate, (left_len, suffix)) in enumerate(
            zip(valid_candidates, batch_spans)
        ):
            score = sum(
                scores[idx, left_len + i - 1, tid].item()
                for i, tid in enumerate(suffix)
            ) / len(suffix)
            scored.append((candidate, score))

        return [cand for cand, _ in sorted(scored, key=lambda pair: -pair[1])][:3]

    def spelling_suggestions(self, text, context_before=""):
        """Check every completed word in the draft, preserving exact character spans."""
        results = []
        for match in re.finditer(r"(?<![\w'’@/.-])([A-Za-z]+)(?=[,.!?;:]*\s)", text):
            word = match.group(1)

            # Skip words the user has already taught the keyboard via sent/accepted messages
            if word.lower() in self.user_freq_cache:
                continue

            prefix = context_before + text[:match.start(1)]
            ranked = self._rank_word_candidates(word, prefix)
            if ranked:
                results.append(
                    {
                        "word": word,
                        "start": match.start(1),
                        "end": match.end(1),
                        "candidates": ranked,
                    }
                )
        return results

    def spelling_suggestion(self, text, context_before=""):
        """Backwards-compatible helper returning the latest completed misspelling."""
        suggestions = self.spelling_suggestions(text, context_before)
        return suggestions[-1] if suggestions else None

    def clear_user_cache(self):
        self.user_freq_cache.clear()

    def _get_next_token_log_probs(self, context_text: str) -> torch.Tensor:
        if not context_text.strip():
            context_text = self.tokenizer.bos_token or "</s>"

        cached_ctx, cached_probs = self._last_log_probs_cache
        if cached_ctx == context_text and cached_probs is not None:
            return cached_probs

        inputs = self.tokenizer(
            context_text,
            return_tensors="pt",
            truncation=True,
            max_length=128,
        ).to(self.device)

        with torch.no_grad():
            outputs = self.model(**inputs)
            next_logits = outputs.logits[0, -1, :].float().cpu()
            log_probs = torch.log_softmax(next_logits, dim=-1)

        self._last_log_probs_cache = (context_text, log_probs)
        return log_probs

    def suggest_punctuation(self, input_text: str):
        """Scores {'.', ',', '?', '!'} via OPT-125M for the current draft."""
        if len(self.punct_ids) == 0:
            return None

        stripped = input_text.rstrip()
        if not stripped or not stripped[-1].isalnum():
            return None

        # Require at least one completed word (trailing space or 2+ words)
        if not input_text.endswith(" ") and " " not in stripped:
            return None

        log_probs = self._get_next_token_log_probs(stripped)
        punct_scores = log_probs[self.punct_tensor]
        probs = torch.softmax(punct_scores, dim=-1)
        best_idx = int(torch.argmax(probs).item())
        best_token_id = self.punct_ids[best_idx]
        return self.id_to_word[best_token_id], round(probs[best_idx].item(), 4)

    def suggest(self, input_text: str, top_k: int = 3, cache_weight: float = 0.35):
        start_time = time.perf_counter()

        if not input_text:
            latency_ms = (time.perf_counter() - start_time) * 1000
            return [("I", 0.32), ("Hi", 0.25), ("Hey", 0.18)], round(latency_ms, 2), "Starter"

        if input_text.endswith(" "):
            mode = "Next-Word"
            context_prefix = input_text.rstrip()
            partial_prefix = ""
        else:
            mode = "Prefix-Completion"
            parts = input_text.rsplit(" ", 1)
            if len(parts) == 2:
                context_prefix, partial_prefix = parts[0], parts[1]
            else:
                context_prefix, partial_prefix = "", parts[0]

        log_probs = self._get_next_token_log_probs(context_prefix).clone()

        if self.user_freq_cache and cache_weight > 0:
            for cached_word, count in self.user_freq_cache.items():
                for tok_id in self.word_to_ids.get(cached_word, []):
                    log_probs[tok_id] += cache_weight * math.log(1.0 + count)

        if mode == "Next-Word":
            candidate_ids = self.whole_word_tensor
        else:
            p_lower = partial_prefix.lower()
            matched_ids = [
                tid
                for tid, w in self.id_to_word.items()
                if w.lower().startswith(p_lower) and len(w) > len(partial_prefix)
            ]
            if not matched_ids:
                custom_matches = []
                for w, _ in sorted(
                    self.user_freq_cache.items(), key=lambda item: -item[1]
                ):
                    if w.startswith(p_lower) and len(w) > len(partial_prefix):
                        display_w = (
                            w.capitalize()
                            if partial_prefix and partial_prefix[0].isupper()
                            else w
                        )
                        custom_matches.append((display_w, 0.90))
                latency_ms = (time.perf_counter() - start_time) * 1000
                return custom_matches[:top_k], round(latency_ms, 2), mode
            candidate_ids = torch.tensor(matched_ids, dtype=torch.long)

        candidate_scores = log_probs[candidate_ids]
        k = min(top_k, len(candidate_ids))
        top_scores, top_indices = torch.topk(candidate_scores, k=k)

        probs = torch.softmax(top_scores, dim=-1).tolist()
        suggestions = []
        for idx, prob in zip(top_indices.tolist(), probs):
            token_id = candidate_ids[idx].item()
            word = self.id_to_word[token_id]
            if partial_prefix and partial_prefix[0].isupper():
                word = word.capitalize()
            suggestions.append((word, round(prob, 4)))

        latency_ms = (time.perf_counter() - start_time) * 1000
        return suggestions, round(latency_ms, 2), mode
