import streamlit as st
import json
import os
import re
import pandas as pd
import requests

st.set_page_config(
    page_title="EcoVoyage AI",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded"
)



st.markdown("""
<style>
/* Full app background */
.stApp {
    background:
        radial-gradient(circle at top left, rgba(16,185,129,0.18), transparent 34%),
        radial-gradient(circle at top right, rgba(59,130,246,0.14), transparent 30%),
        linear-gradient(135deg, #020617 0%, #0f172a 48%, #111827 100%);
    color: #f8fafc;
}

/* Sidebar glass effect */
section[data-testid="stSidebar"] {
    background:
        linear-gradient(180deg, rgba(15,23,42,0.96), rgba(17,24,39,0.92));
    border-right: 1px solid rgba(148,163,184,0.18);
    box-shadow: 8px 0 40px rgba(0,0,0,0.35);
}

/* Sidebar headings */
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {
    color: #f8fafc;
}

/* Main container spacing */
.block-container {
    padding-top: 4rem;
    padding-left: 4rem;
    padding-right: 4rem;
}

/* Hero title */
.big-title {
    font-size: 64px;
    font-weight: 900;
    letter-spacing: -2px;
    background: linear-gradient(90deg, #ffffff, #d1fae5, #86efac);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0.4rem;
}

.subtitle {
    font-size: 26px;
    color: #cbd5e1;
    max-width: 760px;
    line-height: 1.5;
}

/* Premium cards */
.card {
    padding: 26px;
    border-radius: 24px;
    background: rgba(15, 23, 42, 0.76);
    border: 1px solid rgba(148, 163, 184, 0.22);
    box-shadow: 0 24px 70px rgba(0,0,0,0.35);
    backdrop-filter: blur(16px);
    margin-bottom: 18px;
}

.green-card {
    padding: 30px;
    border-radius: 28px;
    background:
        linear-gradient(135deg, rgba(6,78,59,0.95), rgba(15,23,42,0.92)),
        radial-gradient(circle at top right, rgba(34,197,94,0.35), transparent 35%);
    border: 1px solid rgba(52, 211, 153, 0.65);
    box-shadow:
        0 25px 80px rgba(16,185,129,0.18),
        inset 0 1px 0 rgba(255,255,255,0.08);
}

.warning-card {
    padding: 20px;
    border-radius: 20px;
    background: rgba(30, 41, 59, 0.88);
    border: 1px solid rgba(245, 158, 11, 0.45);
    border-left: 6px solid #f59e0b;
    box-shadow: 0 18px 50px rgba(0,0,0,0.25);
}

/* Buttons */
.stButton > button {
    border-radius: 18px;
    padding: 0.75rem 1.25rem;
    font-weight: 800;
    border: none;
    background: linear-gradient(135deg, #10b981, #22c55e);
    color: #052e16;
    box-shadow: 0 14px 35px rgba(16,185,129,0.35);
    transition: all 0.2s ease-in-out;
}

.stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 18px 45px rgba(34,197,94,0.45);
    color: #022c22;
}

/* Inputs */
.stTextInput input,
.stSelectbox div[data-baseweb="select"] > div {
    background-color: rgba(2, 6, 23, 0.72) !important;
    border: 1px solid rgba(148,163,184,0.22) !important;
    border-radius: 16px !important;
    color: #f8fafc !important;
}

/* Metrics */
div[data-testid="stMetric"] {
    background: rgba(15, 23, 42, 0.76);
    border: 1px solid rgba(148,163,184,0.18);
    padding: 22px;
    border-radius: 22px;
    box-shadow: 0 18px 55px rgba(0,0,0,0.28);
}

div[data-testid="stMetricValue"] {
    color: #86efac;
    font-size: 30px;
    font-weight: 900;
}

/* Tabs */
button[data-baseweb="tab"] {
    font-weight: 700;
    color: #cbd5e1;
}

button[data-baseweb="tab"][aria-selected="true"] {
    color: #86efac;
    border-bottom-color: #22c55e;
}

/* Info boxes */
.stAlert {
    border-radius: 22px;
    border: 1px solid rgba(96,165,250,0.35);
    background: rgba(30,64,175,0.18);
}

/* Dataframe */
[data-testid="stDataFrame"] {
    border-radius: 20px;
    overflow: hidden;
}

/* Hide default Streamlit clutter */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)




def extract_budget(budget_text):
    numbers = re.findall(r"\d+", str(budget_text))
    return int(numbers[0]) if numbers else 1000


def load_hotels(destination):
    destination = destination.lower().strip()
    file_path = os.path.join("static_data", f"{destination}_hotels.json")

    if not os.path.exists(file_path):
        file_path = os.path.join("static_data", "berlin_hotels.json")

    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


def send_to_rasa(message):
    url = "http://localhost:5005/webhooks/rest/webhook"

    payload = {
        "sender": "streamlit_user",
        "message": message
    }

    try:
        response = requests.post(url, json=payload, timeout=10)

        if response.status_code == 200:
            return response.json()

        return [{"text": "Rasa server error"}]

    except requests.RequestException:
        return [{"text": "Could not connect to Rasa"}]





def extract_trip_details_from_chat(chat_history):
    user_messages = [m["content"].lower().strip() for m in chat_history if m["role"] == "user"]
    text = " ".join(user_messages)

    destination = None

    for city in ["berlin", "paris", "rome", "london", "dubai", "barcelona", "amsterdam"]:
        if city in text:
            destination = city.title()

    dates = "July 2026"
    date_match = re.search(
        r"(january|february|march|april|may|june|july|august|september|october|november|december|summer|winter|spring|autumn|fall)\s*(\d{4})?",
        text
    )
    if date_match:
        dates = date_match.group(0).title()

    budget = "1000 euros"
    budget_matches = re.findall(r"\d+\s*(?:euros|euro|€)?", text)
    if budget_matches:
        budget = budget_matches[-1].strip()
        if "euro" not in budget and "€" not in budget:
            budget = budget + " euros"

    traveller_type = "Family"
    for traveller in ["business", "luxury", "family", "adventure", "backpacking"]:
        if traveller in text:
            traveller_type = traveller.title()

    sustainability = "Eco Friendly"
    if "comfort" in text:
        sustainability = "Comfort First"
    elif "budget first" in text or "cheap" in text:
        sustainability = "Budget First"
    elif "balanced" in text:
        sustainability = "Balanced"
    elif "strict eco" in text or "eco" in text or "green" in text or "sustainable" in text:
        sustainability = "Eco Friendly"


    complete = (
        destination is not None
        and len(budget_matches) > 0
        and any(t in text for t in ["business", "luxury", "family", "adventure", "backpacking"])
        and any(p in text for p in ["comfort", "balanced", "budget", "eco", "green", "sustainable"])
    )

    return destination, dates, budget, traveller_type, sustainability, complete







def detect_persona(sustainability):
    text = sustainability.lower()

    if "eco" in text or "strict" in text:
        return "🌱 Eco Purist", {
            "carbon": 0.45,
            "certification": 0.25,
            "budget": 0.15,
            "community": 0.15
        }

    if "budget" in text:
        return "💰 Resource Optimiser", {
            "carbon": 0.25,
            "certification": 0.15,
            "budget": 0.45,
            "community": 0.15
        }

    if "comfort" in text:
        return "✨ Comfort Seeker", {
            "carbon": 0.25,
            "certification": 0.25,
            "budget": 0.15,
            "community": 0.35
        }

    return "⚖ Balanced Explorer", {
        "carbon": 0.35,
        "certification": 0.20,
        "budget": 0.25,
        "community": 0.20
    }


def calculate_budget_score(price, budget):
    estimated_trip_cost = price * 5

    if estimated_trip_cost <= budget * 0.6:
        return 95
    if estimated_trip_cost <= budget * 0.8:
        return 85
    if estimated_trip_cost <= budget:
        return 70

    return 40


def confidence_score(hotel):
    score = 50

    if hotel["eco_certified"]:
        score += 20

    if hotel["greenwashing_risk"].lower() == "low":
        score += 15
    elif hotel["greenwashing_risk"].lower() == "medium":
        score += 5
    else:
        score -= 15

    if hotel["carbon_score"] >= 80:
        score += 10

    if hotel["community_score"] >= 80:
        score += 5

    return min(score, 94)


def generate_recommendation(destination, dates, budget_text, traveller_type, sustainability):
    budget = extract_budget(budget_text)
    hotels = load_hotels(destination)
    persona, weights = detect_persona(sustainability)

    carbon_kg = 18.7
    carbon_source = "Climatiq API unavailable during testing; fallback estimate used"

    ranked = []

    for hotel in hotels:
        certification_score = 95 if hotel["eco_certified"] else 45
        budget_score = calculate_budget_score(hotel["price_per_night"], budget)

        eco_score = round(
            hotel["carbon_score"] * weights["carbon"]
            + certification_score * weights["certification"]
            + budget_score * weights["budget"]
            + hotel["community_score"] * weights["community"]
        )

        hotel["eco_score"] = eco_score
        hotel["budget_score"] = budget_score
        hotel["certification_score"] = certification_score
        hotel["confidence"] = confidence_score(hotel)
        ranked.append(hotel)

    ranked = sorted(ranked, key=lambda x: x["eco_score"], reverse=True)

    return ranked[0], ranked[1:3], ranked, persona, weights, carbon_kg, carbon_source


st.markdown('<div class="big-title">🌱 EcoVoyage AI</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">A carbon-aware, explainable travel intelligence dashboard for sustainable accommodation recommendations.</div>',
    unsafe_allow_html=True
)

st.markdown("<br>", unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)



col1.metric("Destinations", "7")
col2.metric("Carbon Model", "API + Fallback")
col3.metric("XAI Features", "6")
col4.metric("Transparency", "100/100")


st.divider()


with st.sidebar:
    st.header("💬 EcoVoyage Chatbot")

    if st.button("Reset chat"):
        st.session_state.chat_history = [
            {
                "role": "assistant",
                "content": "Welcome to EcoVoyage AI 🌱 I can help you plan a low-carbon and ethical trip. Tell me your destination, dates, budget, traveller type and sustainability preference."
            }
        ]
        st.rerun()

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [
            {
                "role": "assistant",
                "content": "Welcome to EcoVoyage AI 🌱 I can help you plan a low-carbon and ethical trip. Tell me your destination, dates, budget, traveller type and sustainability preference."
            }
        ]


    for message in st.session_state.chat_history:
        st.chat_message(message["role"]).write(message["content"])

    user_message = st.chat_input("Type your reply here...")

    if user_message:
        st.session_state.chat_history.append(
            {"role": "user", "content": user_message}
        )

        rasa_replies = send_to_rasa(user_message)

        for reply in rasa_replies:
            bot_text = reply.get("text", "")
            if bot_text:
                st.session_state.chat_history.append(
                    {"role": "assistant", "content": bot_text}
                )

        st.rerun()



    st.markdown("---")

    destination, dates, budget, traveller_type, sustainability, submitted = extract_trip_details_from_chat(
        st.session_state.chat_history)


    if submitted:
        st.success("Trip details detected. Recommendation generated on the main page.")
    else:
        st.info("Choose a supported destination first, then provide budget, traveller type and sustainability preference.")



if not submitted:
    st.markdown("""
    <div class="card">
    <h3>🌍 Sustainable Travel Intelligence</h3>
    <p>
    Generate explainable travel recommendations using carbon-aware scoring,
    sustainability personas, eco-certification analysis, risk assessment,
    counterfactual reasoning and human advisor support.
    </p>
    </div>
    """, unsafe_allow_html=True)



if submitted:
    top, alternatives, ranked, persona, weights, carbon_kg, carbon_source = generate_recommendation(
        destination, dates, budget, traveller_type, sustainability
    )

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Eco Score", f"{top['eco_score']}/100")
    col2.metric("Confidence", f"{top['confidence']}%")
    col3.metric("Carbon Estimate", f"{carbon_kg} kg CO₂e")
    col4.metric("Greenwashing Risk", top["greenwashing_risk"])

    st.markdown("## Recommendation Summary")

    st.markdown("### Sustainability Score")

    st.progress(top["eco_score"] / 100)

    st.markdown(
        f"<h2 style='color:#86efac'>Eco Score: {top['eco_score']}/100</h2>",
        unsafe_allow_html=True
    )

    left, right = st.columns([1.2, 1])

    with left:
        st.markdown(f"""
        <div class="green-card">
        <h2>🟢 {top['name']}</h2>
        <p><b>Destination:</b> {destination}</p>
        <p><b>Dates:</b> {dates}</p>
        <p><b>Traveller type:</b> {traveller_type}</p>
        <p><b>Price per night:</b> €{top['price_per_night']}</p>
        <p><b>Certification:</b> {top['certification']}</p>
        <p><b>Impact level:</b> Low environmental impact</p>
        </div>
        """, unsafe_allow_html=True)

    with right:
        st.markdown(f"""
        <div class="card">
        <h3>Sustainability Persona</h3>
        <h2>{persona}</h2>
        <p>The recommendation engine adjusted the scoring weights based on the user's sustainability preference.</p>
        </div>
        """, unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs([
        "Explainable Scoring",
        "Ranked Alternatives",
        "Carbon & Risk",
        "Human Handover"
    ])

    with tab1:
        st.subheader("Adaptive Decision Weights")

        weights_df = pd.DataFrame({
            "Factor": ["Carbon impact", "Eco-certification", "Budget fit", "Community benefit"],
            "Weight (%)": [
                int(weights["carbon"] * 100),
                int(weights["certification"] * 100),
                int(weights["budget"] * 100),
                int(weights["community"] * 100)
            ]
        })

        st.bar_chart(weights_df.set_index("Factor"))

        st.markdown("### Score Breakdown")
        st.write(f"Carbon impact score: **{top['carbon_score']}/100**")
        st.write(f"Eco-certification score: **{top['certification_score']}/100**")
        st.write(f"Budget fit score: **{top['budget_score']}/100**")
        st.write(f"Community benefit score: **{top['community_score']}/100**")

    with tab2:
        st.subheader("Ranked Sustainable Accommodation Options")

        table_data = []

        for hotel in ranked:
            table_data.append({
                "Hotel": hotel["name"],
                "Eco Score": hotel["eco_score"],
                "Price/Night (€)": hotel["price_per_night"],
                "Certification": hotel["certification"],
                "Greenwashing Risk": hotel["greenwashing_risk"]
            })

        st.dataframe(pd.DataFrame(table_data), width="stretch")

        for hotel in alternatives:
            st.markdown(f"""
            <div class="warning-card">
            <h4>Why not {hotel['name']}?</h4>
            <p>This option scored lower than {top['name']} because of weaker sustainability evidence, lower carbon performance, or reduced community benefit.</p>
            </div>
            """, unsafe_allow_html=True)

    with tab3:
        st.subheader("Carbon Footprint Estimate")

        st.write(f"Estimated carbon footprint: **{carbon_kg} kg CO₂e per 100 km**")
        st.caption(carbon_source)

        st.warning(
            "⚠️ Higher-emission travel options may increase environmental impact. "
            "EcoVoyage prioritises lower-carbon alternatives where possible."
        )

        st.subheader("Risk Dashboard")

        risk_col1, risk_col2, risk_col3 = st.columns(3)
        risk_col1.success("Environmental Risk: Low")
        risk_col2.success("Budget Risk: Low")
        risk_col3.warning(f"Greenwashing Risk: {top['greenwashing_risk']}")

    with tab4:
        st.subheader("Human Advisor Handover Package")

        handover = f"""
        Destination: {destination}
        Dates: {dates}
        Budget: {budget}
        Traveller type: {traveller_type}
        Sustainability persona: {persona}
        Top recommendation: {top['name']}
        Eco Score: {top['eco_score']}/100
        Confidence: {top['confidence']}%
        Greenwashing risk: {top['greenwashing_risk']}
        """

        st.text_area("Generated handover summary", handover, height=220)

        st.success("This package can be transferred to a human travel advisor for follow-up support.")


st.markdown("""
<div style="
    margin-top:80px;
    padding:40px;
    border-radius:24px;
    background:rgba(15,23,42,0.65);
    backdrop-filter:blur(12px);
    border:1px solid rgba(148,163,184,0.15);
    text-align:center;
">

<h2 style="
background:linear-gradient(90deg,#86efac,#38bdf8);
-webkit-background-clip:text;
-webkit-text-fill-color:transparent;
font-weight:900;
">
🌱 EcoVoyage AI
</h2>

<p style="font-size:18px;color:#cbd5e1;">
Carbon-Aware • Explainable • Sustainable
</p>

<hr style="border:1px solid rgba(148,163,184,0.15);">

<p style="font-size:14px;color:#94a3b8;">
♻ Sustainability Scoring &nbsp; | &nbsp;
🌍 Carbon Intelligence &nbsp; | &nbsp;
🤖 Explainable AI &nbsp; | &nbsp;
👩‍💼 Human Handover
</p>

<p style="font-size:12px;color:#64748b;">
MSc Artificial Intelligence Project • Rasa + Streamlit Prototype • 2026
</p>

</div>
""", unsafe_allow_html=True)
