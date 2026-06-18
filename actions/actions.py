from typing import Any, Text, Dict, List
import json
import os
import re
import requests
from dotenv import load_dotenv

from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher

load_dotenv()


class ActionGenerateEcoRecommendation(Action):

    def name(self) -> Text:
        return "action_generate_eco_recommendation"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:

        destination = tracker.get_slot("destination") or "Berlin"
        dates = tracker.get_slot("dates") or "your dates"
        budget_text = tracker.get_slot("budget") or "1000 euros"
        travel_style = tracker.get_slot("travel_style") or "balanced"
        sustainability = tracker.get_slot("sustainability") or "balanced"

        budget = self.extract_budget(budget_text)
        hotels = self.load_hotels(destination)
        persona = self.detect_persona(sustainability)
        weights = self.get_weights(persona)

        carbon_kg, climatiq_carbon_score, carbon_source = self.get_climatiq_carbon_estimate(
            distance_km=100
        )

        ranked_hotels = []

        for hotel in hotels:
            certification_score = 95 if hotel["eco_certified"] else 45
            budget_score = self.calculate_budget_score(hotel["price_per_night"], budget)

            carbon_score = (
                round((hotel["carbon_score"] + climatiq_carbon_score) / 2)
                if climatiq_carbon_score is not None
                else hotel["carbon_score"]
            )

            eco_score = round(
                carbon_score * weights["carbon"]
                + certification_score * weights["certification"]
                + budget_score * weights["budget"]
                + hotel["community_score"] * weights["community"]
            )

            hotel["carbon_score"] = carbon_score   



            confidence_score = self.calculate_confidence_score(
                hotel["eco_certified"],
                hotel["greenwashing_risk"],
                hotel["carbon_score"],
                hotel["community_score"]
            )

            hotel["certification_score"] = certification_score
            hotel["budget_score"] = budget_score
            hotel["eco_score"] = eco_score
            hotel["confidence_score"] = confidence_score
            hotel["risk_dashboard"] = self.calculate_risks(
                eco_score,
                budget_score,
                hotel["greenwashing_risk"],
                hotel["carbon_score"]
            )

            ranked_hotels.append(hotel)

        ranked_hotels = sorted(ranked_hotels, key=lambda x: x["eco_score"], reverse=True)

        top = ranked_hotels[0]
        alternatives = ranked_hotels[1:3]

        impact_icon, impact_label = self.get_impact_label(top["eco_score"])
        confidence_label = self.get_confidence_label(top["confidence_score"])
        risks = top["risk_dashboard"]

        why_not_text = self.generate_why_not_explanations(top, alternatives)
        ethical_review = self.generate_ethical_review(top)
        transparency_report = self.generate_transparency_report(top["confidence_score"])
        persona_explanation = self.generate_persona_explanation(persona, weights)
        counterfactual_text = self.generate_counterfactual_analysis(persona, alternatives)
        tradeoff_text = self.generate_tradeoff_matrix(ranked_hotels)

        transport = self.recommend_transport(travel_style)
        activity = self.recommend_activity(travel_style)

        formula = (
            f"{weights['carbon']} × carbon "
            f"+ {weights['certification']} × certification "
            f"+ {weights['budget']} × budget fit "
            f"+ {weights['community']} × community benefit"
        )

        alternatives_text = ""
        for index, hotel in enumerate(alternatives, start=1):
            alternatives_text += (
                f"\n**Alternative {index}: {hotel['name']}**\n"
                f"- Eco Score: {hotel['eco_score']}/100\n"
                f"- Confidence: {hotel['confidence_score']}%\n"
                f"- Certification: {hotel['certification']}\n"
                f"- Price per night: €{hotel['price_per_night']}\n"
                f"- Greenwashing risk: {hotel['greenwashing_risk']}\n"
            )

        message = f"""
{impact_icon} **EcoVoyage XAI: Sustainable Travel Decision-Support Recommendation**

**Trip profile**
- Destination: {destination}
- Dates: {dates}
- Budget: {budget_text}
- Traveller type: {travel_style}
- Sustainability input: {sustainability}

## Carbon Footprint Estimate
- Estimated carbon footprint: {carbon_kg if carbon_kg is not None else "Unavailable"} kg CO₂e per 100 km
- Carbon data source: {carbon_source}

## Sustainability Persona Detected

{persona_explanation}

## Top Recommendation: {top['name']}

**Explainable Eco Score:** {top['eco_score']}/100  
**Impact level:** {impact_label}  
**Recommendation Confidence:** {top['confidence_score']}% ({confidence_label})

**Price per night:** €{top['price_per_night']}  
**Certification:** {top['certification']}  
**Greenwashing risk:** {top['greenwashing_risk']}

## Explainable Scoring Model

**Eco Score Formula**  
{formula}

**Score breakdown**
- Carbon impact score: {top['carbon_score']}/100
- Eco-certification score: {top['certification_score']}/100
- Budget fit score: {top['budget_score']}/100
- Community benefit score: {top['community_score']}/100

## Risk Dashboard

- Environmental risk: {risks["environmental"]}
- Budget risk: {risks["budget"]}
- Greenwashing risk: {risks["greenwashing"]}
- Transport risk: {risks["transport"]}
- Overall decision risk: {risks["overall"]}

## Suggested Low-Carbon Itinerary Logic

- Transport: {transport}
- Accommodation: {top['name']}
- Activity: {activity}
- Carbon offset: use verified offsets only after reducing avoidable emissions

## Ranked Alternatives
{alternatives_text}

## Why Not? Explanation Engine

{why_not_text}

## Counterfactual AI Analysis

{counterfactual_text}

## Sustainability Trade-Off Matrix

{tradeoff_text}

## Ethical Sustainability Review

{ethical_review}

## Explainability & Transparency Report

{transparency_report}

## Human Advisor Handover Summary

Destination: {destination}; Dates: {dates}; Budget: {budget_text}; Style: {travel_style}; Persona: {persona}; Top recommendation: {top['name']}; Eco Score: {top['eco_score']}/100; Confidence: {top['confidence_score']}%; Overall risk: {risks["overall"]}.
"""

        dispatcher.utter_message(text=message)
        return []
   


    def get_climatiq_carbon_estimate(self, distance_km: int = 100):
        api_key = os.getenv("CLIMATIQ_API_KEY")

        if not api_key:
            return None, None, "Climatiq API key missing"

        url = "https://api.climatiq.io/data/v1/estimate"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "emission_factor": {
                 "activity_id": "passenger_vehicle-vehicle_type_car-fuel_source_petrol-engine_size_na-vehicle_age_na",
                "data_version": "^21"
            },
            "parameters": {
                "distance": distance_km,
                "distance_unit": "km"
            }
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)

            if response.status_code == 200:
                data = response.json()
                carbon_kg = round(data.get("co2e", 0), 2)
                carbon_score = self.convert_carbon_to_score(carbon_kg)
                return carbon_kg, carbon_score, "Live Climatiq API estimate"



            fallback_carbon_kg = 18.7
            fallback_carbon_score = self.convert_carbon_to_score(fallback_carbon_kg)
            return fallback_carbon_kg, fallback_carbon_score, f"Climatiq API unavailable ({response.status_code}); fallback estimate used"
           



        except requests.RequestException as error:
            return None, None, f"Climatiq request failed: {error}"

    def convert_carbon_to_score(self, carbon_kg: float) -> int:
        if carbon_kg <= 10:
            return 95
        if carbon_kg <= 20:
            return 90
        if carbon_kg <= 40:
            return 80
        if carbon_kg <= 70:
            return 65
        return 50    





      

    def load_hotels(self, destination: str) -> List[Dict[str, Any]]:
        destination = destination.lower().strip()

        file_path = os.path.join(
            os.getcwd(),
            "static_data",
            f"{destination}_hotels.json"
        )

        if not os.path.exists(file_path):
            file_path = os.path.join(
                os.getcwd(),
                "static_data",
                "berlin_hotels.json"
            )

        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)



            

    def extract_budget(self, budget_text: str) -> int:
        numbers = re.findall(r"\d+", budget_text)
        if numbers:
            return int(numbers[0])
        return 1000

    def detect_persona(self, sustainability: str) -> str:
        text = sustainability.lower()

        if "strict" in text or "eco" in text or "green" in text or "carbon" in text:
            return "🌱 Eco Purist"
        if "budget" in text or "cheap" in text or "affordable" in text:
            return "💰 Resource Optimiser"
        if "comfort" in text or "luxury" in text or "convenient" in text:
            return "✨ Comfort Seeker"
        if "community" in text or "local" in text or "culture" in text:
            return "🏛 Community Supporter"

        return "⚖ Balanced Explorer"

    def get_weights(self, persona: str) -> Dict[str, float]:
        if "Eco Purist" in persona:
            return {"carbon": 0.45, "certification": 0.25, "budget": 0.15, "community": 0.15}
        if "Resource Optimiser" in persona:
            return {"carbon": 0.25, "certification": 0.15, "budget": 0.45, "community": 0.15}
        if "Comfort Seeker" in persona:
            return {"carbon": 0.25, "certification": 0.25, "budget": 0.15, "community": 0.35}
        if "Community Supporter" in persona:
            return {"carbon": 0.25, "certification": 0.20, "budget": 0.15, "community": 0.40}

        return {"carbon": 0.35, "certification": 0.20, "budget": 0.25, "community": 0.20}

    def generate_persona_explanation(self, persona: str, weights: Dict[str, float]) -> str:
        return (
            f"**Selected persona:** {persona}\n\n"
            f"**Adaptive decision weights**\n"
            f"- Carbon impact: {int(weights['carbon'] * 100)}%\n"
            f"- Eco-certification: {int(weights['certification'] * 100)}%\n"
            f"- Budget fit: {int(weights['budget'] * 100)}%\n"
            f"- Community benefit: {int(weights['community'] * 100)}%"
        )

    def generate_counterfactual_analysis(
        self,
        current_persona: str,
        alternatives: List[Dict[str, Any]]
    ) -> str:
        if not alternatives:
            return "No counterfactual comparison available."

        alt = alternatives[0]

        if "Eco Purist" in current_persona:
            scenario = "💰 Resource Optimiser"
            explanation = (
                f"If you prioritised cost over sustainability, the system would "
                f"consider {alt['name']} more attractive."
            )
        else:
            scenario = "🌱 Eco Purist"
            explanation = (
                "If you prioritised sustainability more strongly, the system would "
                "increase the importance of carbon impact and certification evidence."
            )

        return f"""
Current Persona: {current_persona}

Alternative Scenario: {scenario}

Alternative Recommendation:
{alt['name']}

Alternative Eco Score:
{alt['eco_score']}/100

Estimated Trade-Off:
- Lower accommodation cost may be possible
- Sustainability score may decrease
- Greenwashing confidence may change depending on certification strength

Explanation:
{explanation}
"""

    def generate_tradeoff_matrix(self, ranked_hotels: List[Dict[str, Any]]) -> str:
        output = ""

        for hotel in ranked_hotels:
            sustainability = "High" if hotel["eco_score"] >= 85 else "Medium" if hotel["eco_score"] >= 70 else "Low"
            community = "High" if hotel["community_score"] >= 80 else "Medium"
            cost = "Low" if hotel["price_per_night"] < 100 else "Medium"

            output += (
                f"**{hotel['name']}**\n"
                f"- Sustainability: {sustainability}\n"
                f"- Cost: {cost}\n"
                f"- Community Impact: {community}\n"
                f"- Greenwashing Risk: {hotel['greenwashing_risk']}\n\n"
            )

        return output

    def calculate_budget_score(self, price_per_night: int, total_budget: int) -> int:
        estimated_trip_cost = price_per_night * 5

        if estimated_trip_cost <= total_budget * 0.6:
            return 95
        if estimated_trip_cost <= total_budget * 0.8:
            return 85
        if estimated_trip_cost <= total_budget:
            return 70
        return 40

    def calculate_confidence_score(
        self,
        eco_certified: bool,
        greenwashing_risk: str,
        carbon_score: int,
        community_score: int
    ) -> int:
        score = 50

        if eco_certified:
            score += 20
        else:
            score -= 10

        if greenwashing_risk.lower() == "low":
            score += 15
        elif greenwashing_risk.lower() == "medium":
            score += 5
        else:
            score -= 15

        if carbon_score >= 80:
            score += 10
        elif carbon_score < 60:
            score -= 10

        if community_score >= 80:
            score += 5

        return max(0, min(score, 94))

    def calculate_risks(
        self,
        eco_score: int,
        budget_score: int,
        greenwashing_risk: str,
        carbon_score: int
    ) -> Dict[str, str]:
        environmental = "Low" if eco_score >= 85 else "Medium" if eco_score >= 70 else "High"
        budget = "Low" if budget_score >= 85 else "Medium" if budget_score >= 70 else "High"
        transport = "Low" if carbon_score >= 85 else "Medium" if carbon_score >= 70 else "High"

        risk_values = [environmental, budget, greenwashing_risk, transport]

        if "High" in risk_values:
            overall = "High"
        elif risk_values.count("Medium") >= 2:
            overall = "Medium"
        else:
            overall = "Low"

        return {
            "environmental": environmental,
            "budget": budget,
            "greenwashing": greenwashing_risk,
            "transport": transport,
            "overall": overall
        }

    def generate_why_not_explanations(
        self,
        top: Dict[str, Any],
        alternatives: List[Dict[str, Any]]
    ) -> str:
        output = ""

        for hotel in alternatives:
            reasons = []

            if hotel["eco_score"] < top["eco_score"]:
                reasons.append(f"lower Eco Score ({hotel['eco_score']}/100 vs {top['eco_score']}/100)")
            if hotel["certification_score"] < top["certification_score"]:
                reasons.append("weaker sustainability certification evidence")
            if hotel["carbon_score"] < top["carbon_score"]:
                reasons.append("weaker carbon performance")
            if hotel["community_score"] < top["community_score"]:
                reasons.append("lower community benefit score")
            if hotel["greenwashing_risk"].lower() != "low":
                reasons.append(f"{hotel['greenwashing_risk']} greenwashing risk")
            if hotel["price_per_night"] < top["price_per_night"]:
                reasons.append("it is cheaper, but sustainability evidence is weaker")

            output += f"**Why not {hotel['name']}?**\n"
            for reason in reasons:
                output += f"- {reason}\n"
            output += "\n"

        return output

    def generate_ethical_review(self, hotel: Dict[str, Any]) -> str:
        positives = []
        concerns = []

        if hotel["eco_certified"]:
            positives.append("Recognised sustainability certification found")
        else:
            concerns.append("No recognised third-party eco-certification found")

        if hotel["carbon_score"] >= 85:
            positives.append("Strong carbon performance")
        else:
            concerns.append("Carbon performance should be verified before booking")

        if hotel["community_score"] >= 80:
            positives.append("Local community benefit appears strong")
        else:
            concerns.append("Community benefit evidence is limited")

        if hotel["greenwashing_risk"].lower() == "low":
            positives.append("Low greenwashing risk")
        else:
            concerns.append("Sustainability claims may require manual verification")

        text = "**Positive indicators**\n"
        for item in positives:
            text += f"✓ {item}\n"

        text += "\n**Potential concerns**\n"
        if concerns:
            for item in concerns:
                text += f"⚠ {item}\n"
        else:
            text += "No major ethical concerns detected from available prototype data.\n"

        return text

    def generate_transparency_report(self, confidence_score: int) -> str:
        transparency_score = 100

        return f"""
Decision Transparency Score: {transparency_score}/100

Transparency Features:
✓ Scoring formula disclosed
✓ Adaptive persona weights disclosed
✓ Alternative recommendations disclosed
✓ Why-not explanations provided
✓ Counterfactual analysis provided
✓ Ethical sustainability review provided

Recommendation Confidence:
{confidence_score}%

Transparency Rating:
Excellent
"""

    def get_confidence_label(self, score: int) -> str:
        if score >= 90:
            return "Very high confidence"
        if score >= 75:
            return "High confidence"
        if score >= 60:
            return "Medium confidence"
        return "Low confidence"

    def get_impact_label(self, score: int):
        if score >= 85:
            return "🟢", "Low environmental impact"
        if score >= 70:
            return "🟠", "Moderate environmental impact"
        return "🔴", "High environmental impact"

    def recommend_transport(self, travel_style: str) -> str:
        text = travel_style.lower()

        if "business" in text:
            return "rail-first route with flexible arrival windows"
        if "luxury" in text:
            return "premium rail or verified low-emission private transfer"
        if "family" in text:
            return "family-friendly public transport route"
        if "adventure" in text:
            return "train plus regional public transport"

        return "train or coach-based low-carbon route"

    def recommend_activity(self, travel_style: str) -> str:
        text = travel_style.lower()

        if "business" in text:
            return "locally hosted cultural walking experience after meetings"
        if "luxury" in text:
            return "eco-certified local dining and heritage experience"
        if "family" in text:
            return "low-impact nature and community activities"
        if "adventure" in text:
            return "guided low-impact outdoor experience"

        return "community-led local experience"