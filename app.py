import inspect
import streamlit as st
import streamlit.components.v1 as components
from predictor import OPTKeyboardPredictor, VARIANT_METADATA

PUNCTUATION_SYMBOLS = {".", ",", "?", "!"}

st.set_page_config(
    page_title="OPT Smart Mobile Keyboard",
    page_icon="📱",
    layout="centered",
)

st.markdown(
    """
    <style>
    .stButton > button {
        width: 100%;
        border-radius: 12px;
        font-weight: 600;
        padding: 0.55rem 0.75rem;
    }
    .keyboard-hint {
        font-size: 0.85rem;
        color: #666;
        margin-bottom: 0.5rem;
    }
    .keyboard-input-label {
        font-size: 0.875rem;
        font-weight: 500;
        margin-bottom: 0.35rem;
    }
    /* Force input bar + WhatsApp send button onto a single horizontal row on ALL screen widths */
    [data-testid="stHorizontalBlock"]:has(.st-key-whatsapp_send_btn) {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        align-items: center !important;
        gap: 0.45rem !important;
        width: 100% !important;
    }
    [data-testid="stHorizontalBlock"]:has(.st-key-whatsapp_send_btn) > [data-testid="stColumn"]:first-child,
    [data-testid="stHorizontalBlock"]:has(.st-key-whatsapp_send_btn) > [data-testid="column"]:first-child {
        flex: 1 1 auto !important;
        min-width: 0 !important;
        width: auto !important;
    }
    [data-testid="stHorizontalBlock"]:has(.st-key-whatsapp_send_btn) > [data-testid="stColumn"]:last-child,
    [data-testid="stHorizontalBlock"]:has(.st-key-whatsapp_send_btn) > [data-testid="column"]:last-child {
        flex: 0 0 2.6rem !important;
        min-width: 2.6rem !important;
        max-width: 2.6rem !important;
        width: 2.6rem !important;
    }
    /* Rounded WhatsApp-style text bar */
    [data-testid="stTextInput"] div[data-baseweb="input"] {
        border-radius: 20px !important;
        padding-left: 0.35rem !important;
    }
    /* Circular WhatsApp-style inline send button beside the input bar */
    .st-key-whatsapp_send_btn button,
    .stButton > button[kind="primary"] {
        background-color: #25D366 !important;
        border-color: #25D366 !important;
        color: #FFFFFF !important;
        border-radius: 50% !important;
        width: 2.6rem !important;
        height: 2.6rem !important;
        min-height: 2.6rem !important;
        padding: 0 !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        font-size: 1.1rem !important;
        line-height: 1 !important;
        box-shadow: 0 2px 6px rgba(37, 211, 102, 0.35) !important;
        transition: background-color 0.15s ease, transform 0.1s ease !important;
    }
    .st-key-whatsapp_send_btn button:hover,
    .stButton > button[kind="primary"]:hover {
        background-color: #1EBE5D !important;
        border-color: #1EBE5D !important;
        color: #FFFFFF !important;
    }
    .st-key-whatsapp_send_btn button:active,
    .stButton > button[kind="primary"]:active {
        background-color: #128C7E !important;
        border-color: #128C7E !important;
        transform: scale(0.95);
    }
    /* Keep the 4 suggestion chips on a single horizontal row on mobile screens */
    [data-testid="stHorizontalBlock"]:has(.st-key-empty_punct),
    [data-testid="stHorizontalBlock"]:has([class*="st-key-punct_"]) {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 0.35rem !important;
    }
    [data-testid="stHorizontalBlock"]:has(.st-key-empty_punct) > [data-testid="stColumn"],
    [data-testid="stHorizontalBlock"]:has(.st-key-empty_punct) > [data-testid="column"],
    [data-testid="stHorizontalBlock"]:has([class*="st-key-punct_"]) > [data-testid="stColumn"],
    [data-testid="stHorizontalBlock"]:has([class*="st-key-punct_"]) > [data-testid="column"] {
        flex: 1 1 0 !important;
        min-width: 0 !important;
        width: auto !important;
    }
    [data-testid="stHorizontalBlock"]:has(.st-key-empty_punct) > [data-testid="stColumn"]:last-child,
    [data-testid="stHorizontalBlock"]:has(.st-key-empty_punct) > [data-testid="column"]:last-child,
    [data-testid="stHorizontalBlock"]:has([class*="st-key-punct_"]) > [data-testid="stColumn"]:last-child,
    [data-testid="stHorizontalBlock"]:has([class*="st-key-punct_"]) > [data-testid="column"]:last-child {
        flex: 0 0 4.1rem !important;
        min-width: 4.1rem !important;
        width: 4.1rem !important;
    }
    @media (max-width: 640px) {
        [data-testid="stHorizontalBlock"]:has(.st-key-empty_punct) button,
        [data-testid="stHorizontalBlock"]:has([class*="st-key-punct_"]) button {
            padding: 0.45rem 0.2rem !important;
            font-size: 0.78rem !important;
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
        }
    }
    /* Tighten vertical spacing around header and mode divider */
    .block-container {
        padding-top: 2rem !important;
    }
    hr.compact-divider {
        margin-top: 0.25rem !important;
        margin-bottom: 0.65rem !important;
        border: none;
        border-top: 1px solid rgba(49, 51, 63, 0.16);
    }
    /* Hide the 0px auto-focus iframe wrapper so it adds no vertical spacing */
    .stElementContainer:has(iframe[height="0"]),
    .element-container:has(iframe[height="0"]) {
        display: none !important;
    }
    /* Auto-growing history box up to a compact max-height, then scrollable */
    div.st-key-solo_history_box,
    div.st-key-chat_history_box {
        max-height: 200px !important;
        max-width: 100% !important;
        overflow-y: auto !important;
        padding: 0.85rem 1rem !important;
        border-radius: 12px !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource(show_spinner="Loading OPT-125M keyboard model...")
def load_predictor(variant: str) -> OPTKeyboardPredictor:
    return OPTKeyboardPredictor.from_variant(variant=variant, device="cpu")


# --- Session State Initialization ---
if "dismissed_spellings" not in st.session_state:
    st.session_state.dismissed_spellings = set()
if "app_mode" not in st.session_state:
    st.session_state.app_mode = "Single-User"
if "typed_text" not in st.session_state:
    st.session_state.typed_text = ""
if "solo_messages" not in st.session_state:
    st.session_state.solo_messages = []
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if st.session_state.get("active_speaker") not in ("User A", "User B"):
    st.session_state.active_speaker = "User A"
if "user_caches" not in st.session_state:
    st.session_state.user_caches = {
        "Solo": {},
        "User A": {},
        "User B": {},
    }
if "focus_tick" not in st.session_state:
    st.session_state.focus_tick = 1


def request_input_focus():
    """Signals the browser to return cursor focus to the main text input."""
    st.session_state.focus_tick += 1


def apply_suggestion(word: str, mode: str):
    """Inserts next word, attaches punctuation directly, or completes partial word."""
    current = st.session_state.typed_text
    if word in PUNCTUATION_SYMBOLS:
        base = current.rstrip()
        st.session_state.typed_text = f"{base}{word} " if base else f"{word} "
    elif mode == "Starter" or not current.strip():
        st.session_state.typed_text = f"{word} "
    elif mode == "Next-Word":
        sep = "" if current.endswith((" ", "\t", "\n")) else " "
        st.session_state.typed_text = f"{current}{sep}{word} "
    else:
        if " " in current:
            prefix_ctx, _ = current.rsplit(" ", 1)
            st.session_state.typed_text = f"{prefix_ctx} {word} "
        else:
            st.session_state.typed_text = f"{word} "


def confirm_suggestion(
    predictor: OPTKeyboardPredictor,
    active_profile: str,
    word: str,
    mode: str,
):
    """Applies the chosen word/symbol, updates personal cache, and keeps focus in input."""
    apply_suggestion(word, mode)
    predictor.user_freq_cache = st.session_state.user_caches[active_profile]
    predictor.update_user_cache(word)
    request_input_focus()


def set_sample_prompt(prompt_text: str):
    st.session_state.typed_text = prompt_text
    st.session_state.dismissed_spellings.clear()
    request_input_focus()


def start_two_user_scenario(opening_msg: str, reply_prefix: str = ""):
    st.session_state.chat_history = [{"sender": "User A", "text": opening_msg}]
    st.session_state.active_speaker = "User B"
    st.session_state.typed_text = reply_prefix
    st.session_state.dismissed_spellings.clear()
    request_input_focus()


def accept_correction(
    predictor: OPTKeyboardPredictor,
    active_profile: str,
    original: str,
    start: int,
    end: int,
    replacement: str,
):
    if st.session_state.typed_text == original:
        st.session_state.typed_text = original[:start] + replacement + original[end:]
        predictor.user_freq_cache = st.session_state.user_caches[active_profile]
        predictor.update_user_cache(replacement)

        # Keep character offsets aligned for any previously dismissed words after this edit
        delta = len(replacement) - (end - start)
        updated_dismissed = set()
        for mode_name, prof_name, dismissed_word, dismissed_start in st.session_state.dismissed_spellings:
            if mode_name == st.session_state.app_mode and prof_name == active_profile:
                if dismissed_start == start:
                    continue
                if dismissed_start > start:
                    dismissed_start += delta
            updated_dismissed.add((mode_name, prof_name, dismissed_word, dismissed_start))
        st.session_state.dismissed_spellings = updated_dismissed

    request_input_focus()


def dismiss_correction(signature):
    st.session_state.dismissed_spellings.add(signature)
    request_input_focus()


def send_current_message(
    predictor: OPTKeyboardPredictor,
    active_profile: str,
    auto_switch: bool = True,
):
    """Callback executed before widget instantiation so clearing typed_text is safe."""
    msg = st.session_state.typed_text.strip()
    if not msg:
        request_input_focus()
        return
    predictor.user_freq_cache = st.session_state.user_caches[active_profile]
    predictor.update_user_cache(msg)
    if st.session_state.app_mode == "Single-User":
        st.session_state.solo_messages.append(msg)
    else:
        st.session_state.chat_history.append({"sender": active_profile, "text": msg})
        if auto_switch:
            st.session_state.active_speaker = (
                "User B" if active_profile == "User A" else "User A"
            )
    st.session_state.typed_text = ""
    st.session_state.dismissed_spellings.clear()
    request_input_focus()


def reset_chat_history():
    """Callback executed before widget instantiation to clear chat and reset to User A."""
    st.session_state.chat_history = []
    st.session_state.active_speaker = "User A"
    st.session_state.typed_text = ""
    st.session_state.dismissed_spellings.clear()
    request_input_focus()


def inject_input_autofocus(focus_tick: int):
    """Focuses the main text input and moves the caret to the end of the text."""
    components.html(
        f"""
        <!-- focus_tick: {focus_tick} -->
        <script>
        (function() {{
            const parentDoc = window.parent.document;
            let attempts = 0;
            function focusInput() {{
                const input = parentDoc.querySelector('[data-testid="stTextInput"] input');
                if (input) {{
                    input.focus({{ preventScroll: true }});
                    const len = input.value ? input.value.length : 0;
                    try {{
                        input.setSelectionRange(len, len);
                    }} catch (e) {{}}
                }}
                attempts += 1;
                if (attempts < 6) {{
                    setTimeout(focusInput, 40);
                }}
            }}
            requestAnimationFrame(focusInput);
        }})();
        </script>
        """,
        height=0,
        width=0,
    )


def render_live_keyboard_input(
    label: str,
    placeholder: str,
    predictor: OPTKeyboardPredictor,
    active_profile: str,
    auto_switch: bool,
    send_tooltip: str,
):
    """Single-line input with real-time keystroke updates, inline send button, and auto-focus."""
    st.markdown(f"<div class='keyboard-input-label'>{label}</div>", unsafe_allow_html=True)
    input_col, send_col = st.columns([7.5, 1])
    with input_col:
        supports_live = "live" in inspect.signature(st.text_input).parameters
        kwargs = {
            "key": "typed_text",
            "placeholder": placeholder,
            "label_visibility": "collapsed",
        }
        if supports_live:
            kwargs["live"] = "150ms"
        st.text_input(label, **kwargs)
    with send_col:
        st.button(
            "➤",
            key="whatsapp_send_btn",
            type="primary",
            help=send_tooltip,
            on_click=send_current_message,
            args=(predictor, active_profile, auto_switch),
        )
    inject_input_autofocus(st.session_state.focus_tick)


def render_history_container(box_key: str):
    """Creates a bordered container that grows with content up to CSS max-height."""
    if "key" in inspect.signature(st.container).parameters:
        return st.container(key=box_key, border=True)
    return st.container(border=True)


# --- Sidebar Controls ---
with st.sidebar:
    st.header("⚙️ Keyboard Engine Settings")
    variant_options = list(VARIANT_METADATA.keys())
    selected_variant = st.selectbox(
        "Model Variant",
        options=variant_options,
        format_func=lambda k: VARIANT_METADATA[k]["label"],
        index=0,
    )

    cache_weight = st.slider(
        "Personalization Boost (λ)",
        min_value=0.0,
        max_value=1.0,
        value=0.35,
        step=0.05,
        help="Boosts words frequently confirmed or sent by the active user.",
    )

    spelling_enabled = st.checkbox("Spelling suggestions", value=True)

    st.divider()
    if st.session_state.app_mode == "Single-User":
        st.subheader("🧪 Single-User Test Prompts")
        samples = [
            "My phone battery is at 1%, do you have a ",
            "Sure, I will meet you at the train ",
            "I am heading to the groc",
            "Hey! Are you free for lun",
        ]
        for idx, sample in enumerate(samples):
            st.button(
                f'Try: "{sample}"',
                key=f"sample_{idx}",
                on_click=set_sample_prompt,
                args=(sample,),
            )
    else:
        st.subheader("💬 Optional Quick Scenarios")
        scenarios = [
            ("Lunch Invite", "Hey! Are you free for lunch today?", ""),
            (
                "Phone Battery",
                "My phone battery is at 1%, do you have a charger?",
                "Yes, I have a ",
            ),
            (
                "Train Meetup",
                "I just arrived at the station, where are you?",
                "I am on my ",
            ),
        ]
        for idx, (label, msg_a, draft_b) in enumerate(scenarios):
            st.button(
                f"Load: {label}",
                key=f"scen_{idx}",
                on_click=start_two_user_scenario,
                args=(msg_a, draft_b),
            )

# Load cached model (no reload needed when switching users or modes)
predictor = load_predictor(selected_variant)

# --- Header & Mode Selector ---
st.title("📱 Context-Aware Mobile Keyboard")
st.caption(
    "BMDS2123 Natural Language Processing • `facebook/opt-125m` + LoRA + Hybrid Prefix-Aware Decoding"
)

current_label = (
    "Single-User"
    if st.session_state.app_mode == "Single-User"
    else "Multi-User (2-Person Chat)"
)
mode_choice = st.segmented_control(
    "Select Interaction Mode",
    options=["Single-User", "Multi-User (2-Person Chat)"],
    default=current_label,
    selection_mode="single",
)
if mode_choice is None:
    mode_choice = current_label

new_mode = (
    "Multi-User"
    if mode_choice == "Multi-User (2-Person Chat)"
    else "Single-User"
)
if new_mode != st.session_state.app_mode:
    st.session_state.app_mode = new_mode
    st.session_state.typed_text = ""
    st.session_state.dismissed_spellings.clear()
    if new_mode == "Multi-User" and not st.session_state.chat_history:
        st.session_state.active_speaker = "User A"
    request_input_focus()
    st.rerun()

st.markdown('<hr class="compact-divider">', unsafe_allow_html=True)

# ==============================================================================
# MODE 1: SINGLE-USER (SOLO TYPING)
# ==============================================================================
if st.session_state.app_mode == "Single-User":
    active_profile = "Solo"
    auto_switch = False
    predictor.user_freq_cache = st.session_state.user_caches[active_profile]

    # Hidden until at least 1 message is sent; expands up to 200px then scrolls
    if st.session_state.solo_messages:
        st.markdown("**Sent Message History**")
        with render_history_container("solo_history_box"):
            for msg in st.session_state.solo_messages:
                st.markdown(f"💬 {msg}")

    render_live_keyboard_input(
        label="Type a message:",
        placeholder="Start typing here...",
        predictor=predictor,
        active_profile=active_profile,
        auto_switch=auto_switch,
        send_tooltip="Send message",
    )

    model_input = st.session_state.typed_text

# ==============================================================================
# MODE 2: MULTI-USER (2-PERSON CONVERSATION)
# ==============================================================================
else:
    ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([2, 1.15, 0.95])
    with ctrl_col1:
        if st.session_state.get("active_speaker") not in ("User A", "User B"):
            st.session_state.active_speaker = "User A"
        st.segmented_control(
            "Active Typist",
            options=["User A", "User B"],
            key="active_speaker",
            selection_mode="single",
            on_change=request_input_focus,
        )
    with ctrl_col2:
        auto_switch = st.checkbox("Auto-switch turn", value=True)
    with ctrl_col3:
        st.button("Reset Chat", on_click=reset_chat_history)

    active_profile = st.session_state.active_speaker
    predictor.user_freq_cache = st.session_state.user_caches[active_profile]

    # Hidden until the first message is sent; expands up to 200px then scrolls
    if st.session_state.chat_history:
        st.markdown("**Sent Message History**")
        with render_history_container("chat_history_box"):
            for item in st.session_state.chat_history:
                is_user_a = item["sender"] == "User A"
                role = "user" if is_user_a else "assistant"
                avatar = "🧑" if is_user_a else "👩"
                with st.chat_message(role, avatar=avatar):
                    st.markdown(f"**{item['sender']}:** {item['text']}")

    badge = "🧑 User A" if active_profile == "User A" else "👩 User B"
    prompt_label = (
        f"Start the conversation as {badge}:"
        if not st.session_state.chat_history
        else f"Message as {badge} (predictions adapt live to chat context):"
    )
    render_live_keyboard_input(
        label=prompt_label,
        placeholder=f"Type {active_profile}'s message here...",
        predictor=predictor,
        active_profile=active_profile,
        auto_switch=auto_switch,
        send_tooltip=f"Send as {active_profile}",
    )

    # Condition predictions on recent chat turns + active user's current draft
    draft = st.session_state.typed_text
    if st.session_state.chat_history:
        recent_turns = " ".join(
            m["text"].strip() for m in st.session_state.chat_history[-2:]
        )
        if not draft.strip():
            model_input = f"{recent_turns} "
        else:
            model_input = f"{recent_turns} {draft}"
    else:
        model_input = draft

# ==============================================================================
# SHARED TOP-3 MOBILE KEYBOARD BAR + CONTEXTUAL PUNCTUATION
# ==============================================================================
draft_for_spelling = st.session_state.typed_text
if not draft_for_spelling:
    st.session_state.dismissed_spellings.clear()

if spelling_enabled and draft_for_spelling:
    preceding_context = ""
    if st.session_state.app_mode == "Multi-User" and st.session_state.chat_history:
        preceding_context = (
            " ".join(m["text"] for m in st.session_state.chat_history[-2:]) + " "
        )

    if hasattr(predictor, "spelling_suggestions"):
        corrections = predictor.spelling_suggestions(draft_for_spelling, preceding_context)
    else:
        single = predictor.spelling_suggestion(draft_for_spelling, preceding_context)
        corrections = [single] if single else []

    for correction in corrections:
        word_sig = (
            st.session_state.app_mode,
            active_profile,
            correction["word"].lower(),
            correction["start"],
        )
        if word_sig in st.session_state.dismissed_spellings:
            continue

        choices = correction["candidates"]
        st.info(f'Did you mean "{choices[0]}" instead of "{correction["word"]}"?')
        correction_cols = st.columns(len(choices) + 1)
        for index, choice in enumerate(choices):
            with correction_cols[index]:
                label = f"Yes — {choice}" if index == 0 else choice
                st.button(
                    label,
                    key=f"correction_{correction['start']}_{index}_{choice}",
                    on_click=accept_correction,
                    args=(
                        predictor,
                        active_profile,
                        draft_for_spelling,
                        correction["start"],
                        correction["end"],
                        choice,
                    ),
                )
        with correction_cols[-1]:
            st.button(
                "No — keep original",
                key=f"dismiss_spelling_{correction['start']}_{correction['word']}",
                on_click=dismiss_correction,
                args=(word_sig,),
            )

suggestions, latency_ms, mode = predictor.suggest(
    model_input,
    top_k=3,
    cache_weight=cache_weight,
)

punct_suggestion = None
if (
    st.session_state.typed_text.strip()
    and hasattr(predictor, "suggest_punctuation")
):
    punct_suggestion = predictor.suggest_punctuation(model_input)

st.markdown(
    f"<div class='keyboard-hint'>Profile: <b>{active_profile}</b> • Mode: <b>{mode}</b> • Latency: <b>{latency_ms:.1f} ms</b> • Footprint: <b>{predictor.variant_info.get('size_label', '')}</b></div>",
    unsafe_allow_html=True,
)

cols = st.columns([1, 1, 1, 0.75])
for i in range(3):
    with cols[i]:
        if i < len(suggestions):
            word, prob = suggestions[i]
            st.button(
                f"{word}  ({prob * 100:.0f}%)",
                key=f"sugg_{active_profile}_{i}_{word}",
                on_click=confirm_suggestion,
                args=(predictor, active_profile, word, mode),
            )
        else:
            st.button("—", key=f"empty_{i}", disabled=True)

with cols[3]:
    if punct_suggestion is not None:
        sym, sym_prob = punct_suggestion
        st.button(
            f"{sym}  ({sym_prob * 100:.0f}%)",
            key=f"punct_{active_profile}_{sym}",
            on_click=confirm_suggestion,
            args=(predictor, active_profile, sym, mode),
        )
    else:
        st.button("—", key="empty_punct", disabled=True)

# Adaptive User Cache Viewer (per active user profile)
with st.expander(f"🧠 Adaptive Vocabulary Cache ({active_profile})"):
    active_cache = st.session_state.user_caches[active_profile]
    if active_cache:
        sorted_cache = sorted(active_cache.items(), key=lambda x: x[1], reverse=True)
        st.write(dict(sorted_cache))
        if st.button(f"Reset {active_profile}'s Cache"):
            st.session_state.user_caches[active_profile].clear()
            st.rerun()
    else:
        st.info(
            f"Tap suggested words or send messages as {active_profile} to build their personal word frequency cache."
        )
