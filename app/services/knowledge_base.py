"""Curated carbon-footprint knowledge base.

A compact, fully self-contained set of question/answer entries covering the
breadth of personal carbon-footprint topics. The chat assistant retrieves the
best-matching entry with TF-IDF similarity, so the app can answer a wide range
of questions with **no external API and no secrets**.

Each entry is a dict:
    topic:    short human-readable label.
    keywords: extra search terms (synonyms / phrasings) to improve matching.
    answer:   the plain-text answer shown to the user.

Keep every value ASCII-only and dependency-free.
"""

from typing import Dict, List

KNOWLEDGE_BASE: List[Dict[str, str]] = [
    {
        "topic": "What is a carbon footprint",
        "keywords": "define meaning carbon footprint co2 emissions explanation what is",
        "answer": (
            "A carbon footprint is the total amount of greenhouse gases - mainly "
            "carbon dioxide (CO2) - released into the atmosphere because of your "
            "activities, measured in kilograms or tonnes of CO2 equivalent "
            "(CO2e). It adds up emissions from travel, food, home energy and the "
            "products you buy."
        ),
    },
    {
        "topic": "What is CO2e",
        "keywords": "co2e carbon dioxide equivalent unit measure greenhouse gas methane",
        "answer": (
            "CO2e (carbon dioxide equivalent) is a single unit that combines all "
            "greenhouse gases by converting them to the amount of CO2 that would "
            "cause the same warming. For example methane is far more potent than "
            "CO2, so a little methane counts as a lot of CO2e."
        ),
    },
    {
        "topic": "Average carbon footprint",
        "keywords": "average typical global per person per capita how much tonnes",
        "answer": (
            "The global average is roughly 4 to 5 tonnes of CO2e per person per "
            "year, but it varies hugely: many wealthy countries average 10 or "
            "more tonnes, while to limit warming to safe levels the sustainable "
            "target is closer to 2 tonnes per person."
        ),
    },
    {
        "topic": "Why reducing your footprint matters",
        "keywords": "why important matter climate change benefit reduce reason",
        "answer": (
            "Cutting your footprint slows climate change, improves air quality, "
            "and often saves money on energy and travel. Individual action also "
            "drives demand for cleaner products and signals to businesses and "
            "governments that low-carbon choices matter."
        ),
    },
    {
        "topic": "Biggest sources of personal emissions",
        "keywords": "biggest largest main sources categories transport food energy flights",
        "answer": (
            "For most people the largest contributors are transport (especially "
            "car travel and flights), home energy (heating and electricity), and "
            "diet (especially red meat and dairy). Focusing on these high-impact "
            "areas gives the biggest reductions."
        ),
    },
    {
        "topic": "Reduce car travel emissions",
        "keywords": "car driving petrol diesel reduce commute transport miles km fuel",
        "answer": (
            "Drive less and smarter: combine trips, car-share, keep tyres "
            "inflated and drive smoothly. Shift shorter journeys to walking, "
            "cycling or public transport, and consider an electric vehicle for "
            "your next car. Replacing even a third of car kilometres with rail or "
            "active travel cuts a large share of transport emissions."
        ),
    },
    {
        "topic": "Electric vehicles",
        "keywords": "ev electric car battery tesla charging cleaner switch worth it",
        "answer": (
            "Electric vehicles produce no tailpipe emissions and, even after "
            "accounting for electricity generation and battery manufacturing, "
            "typically have a much lower lifetime carbon footprint than petrol "
            "cars - especially as the grid gets cleaner. Charging on renewable "
            "electricity maximises the benefit."
        ),
    },
    {
        "topic": "Flying and air travel",
        "keywords": "flight flying plane air travel holiday vacation reduce flights",
        "answer": (
            "Air travel is one of the most carbon-intensive activities per hour. "
            "Fly less by combining trips, choosing direct flights, holidaying "
            "closer to home, and taking trains for shorter journeys. One "
            "long-haul return flight can equal a large share of an average "
            "person's annual footprint."
        ),
    },
    {
        "topic": "Public transport and cycling",
        "keywords": "bus train cycling bike walking public transport active travel",
        "answer": (
            "Trains and buses move many people at once, so per passenger they "
            "emit far less than a private car. Walking and cycling are "
            "essentially zero-carbon and improve your health too. Swapping car "
            "trips for these is one of the easiest everyday wins."
        ),
    },
    {
        "topic": "Diet and food emissions",
        "keywords": "food diet eat meat dairy vegetarian vegan plant based reduce",
        "answer": (
            "Food is a major part of most footprints. Red meat (beef, lamb) and "
            "dairy are the most carbon-intensive, while plants, grains and "
            "legumes are far lower. Shifting several meals a week to plant-based "
            "options, choosing chicken or fish over red meat, and eating "
            "seasonal local produce all help."
        ),
    },
    {
        "topic": "Plant-based and vegan diets",
        "keywords": "vegan vegetarian plant based meat free reduce diet impact",
        "answer": (
            "Vegetarian and vegan diets typically have roughly half the food "
            "footprint of a high-meat diet. You do not have to go fully "
            "plant-based to benefit - even reducing red meat and dairy a few "
            "days a week makes a meaningful difference."
        ),
    },
    {
        "topic": "Food waste",
        "keywords": "food waste leftovers throw away compost reduce wasted",
        "answer": (
            "About a third of food produced is wasted, and that waste carries all "
            "the emissions from growing, transporting and storing it. Plan meals, "
            "store food well, use leftovers, and compost scraps to shrink this "
            "hidden footprint."
        ),
    },
    {
        "topic": "Home electricity use",
        "keywords": "electricity power kwh appliances lights reduce energy bill",
        "answer": (
            "Cut electricity emissions by switching to LED lighting, turning off "
            "standby power, using efficient appliances, and running washing "
            "machines and dishwashers on full loads at lower temperatures. "
            "Switching to a certified renewable tariff can cut the carbon "
            "intensity of your power dramatically."
        ),
    },
    {
        "topic": "Heating and gas",
        "keywords": "heating gas boiler thermostat warm insulation winter reduce",
        "answer": (
            "Heating is often the biggest home energy use. Turning the thermostat "
            "down by one degree, draught-proofing, and improving insulation can "
            "noticeably cut gas use. A well-serviced or upgraded heating system, "
            "and a heat pump where suitable, reduce emissions further."
        ),
    },
    {
        "topic": "Home insulation",
        "keywords": "insulation loft wall draught proofing windows double glazing",
        "answer": (
            "Good insulation keeps heat in, so your heating works less. Loft and "
            "wall insulation, draught-proofing doors and windows, and double "
            "glazing all reduce heat loss, lower bills, and cut the carbon from "
            "heating your home."
        ),
    },
    {
        "topic": "Renewable energy and green tariffs",
        "keywords": "renewable green tariff solar wind clean energy electricity switch",
        "answer": (
            "Choosing a certified renewable electricity tariff means your supply "
            "is matched by wind, solar or hydro generation, sharply lowering the "
            "carbon intensity of your electricity. It is usually one of the "
            "quickest high-impact switches you can make at home."
        ),
    },
    {
        "topic": "Solar panels",
        "keywords": "solar panels pv rooftop generate electricity home renewable",
        "answer": (
            "Rooftop solar panels generate low-carbon electricity for your home "
            "and can cut both your bills and your footprint. They pay back their "
            "manufacturing emissions within a few years and then provide clean "
            "power for decades."
        ),
    },
    {
        "topic": "Heat pumps",
        "keywords": "heat pump air source ground source heating electric replace boiler",
        "answer": (
            "Heat pumps move heat rather than burning fuel, so they deliver "
            "several units of heat per unit of electricity. Running on a clean "
            "grid or renewable tariff, they can dramatically cut heating "
            "emissions compared with a gas boiler."
        ),
    },
    {
        "topic": "Water use",
        "keywords": "water shower bath hot water heating save reduce usage",
        "answer": (
            "Heating water takes energy, so shorter showers, fixing leaks, and "
            "washing clothes at lower temperatures all save carbon as well as "
            "water. Efficient shower heads and only boiling the water you need "
            "add up over time."
        ),
    },
    {
        "topic": "Recycling and waste",
        "keywords": "recycle recycling waste rubbish landfill reduce reuse",
        "answer": (
            "Recycling saves the energy and emissions needed to make new "
            "materials from scratch, and keeps waste out of landfill where it can "
            "release methane. The bigger wins, though, come from reducing and "
            "reusing before you recycle."
        ),
    },
    {
        "topic": "Plastics",
        "keywords": "plastic single use packaging bottles reduce reusable",
        "answer": (
            "Plastics are made from fossil fuels and emit carbon during "
            "production and disposal. Cut single-use plastics by carrying "
            "reusable bottles, bags and containers, and choosing products with "
            "less packaging."
        ),
    },
    {
        "topic": "Shopping and consumer goods",
        "keywords": "shopping buying products goods consumption stuff buy less",
        "answer": (
            "Everything you buy carries embedded emissions from manufacturing and "
            "transport. Buying less, choosing durable and second-hand items, "
            "repairing instead of replacing, and supporting low-carbon brands all "
            "shrink this often-overlooked part of your footprint."
        ),
    },
    {
        "topic": "Fast fashion and clothing",
        "keywords": "clothes clothing fashion textiles fast fashion buy wear",
        "answer": (
            "Clothing has a surprisingly large footprint due to materials, "
            "manufacturing and shipping. Buy fewer, better-quality items, choose "
            "second-hand, repair what you own, and wash at lower temperatures to "
            "extend garment life."
        ),
    },
    {
        "topic": "Digital and streaming footprint",
        "keywords": "internet streaming video email data digital online cloud",
        "answer": (
            "Streaming, cloud storage and devices use electricity in data centres "
            "and networks. The impact per action is small, but it adds up: lower "
            "video resolution when you do not need HD, delete what you do not "
            "use, and keep devices longer to reduce manufacturing emissions."
        ),
    },
    {
        "topic": "Carbon offsetting",
        "keywords": "offset offsetting carbon credits trees compensate neutral",
        "answer": (
            "Offsetting funds projects that cut or absorb emissions - such as "
            "reforestation or renewable energy - to compensate for emissions you "
            "cannot avoid. It is best used after you have reduced as much as "
            "possible, and only with high-quality, verified credits."
        ),
    },
    {
        "topic": "Planting trees",
        "keywords": "trees planting forest reforestation absorb co2 nature",
        "answer": (
            "Trees absorb CO2 as they grow, so planting and protecting forests "
            "helps remove carbon from the atmosphere. It is a valuable "
            "complement to cutting emissions, though it works over many years and "
            "cannot replace reducing fossil-fuel use."
        ),
    },
    {
        "topic": "Net zero",
        "keywords": "net zero carbon neutral target meaning balance emissions",
        "answer": (
            "Net zero means cutting emissions as much as possible and balancing "
            "any remaining emissions by removing an equal amount from the "
            "atmosphere, so your net contribution to warming is zero. For "
            "individuals it means reducing first, then offsetting the rest."
        ),
    },
    {
        "topic": "Scope 1 2 and 3 emissions",
        "keywords": "scope 1 2 3 direct indirect supply chain business categories",
        "answer": (
            "These categories are mainly used by organisations. Scope 1 is direct "
            "emissions you produce (e.g. burning gas), Scope 2 is from the "
            "electricity you buy, and Scope 3 is all other indirect emissions "
            "across your supply chain - usually the largest and hardest to cut."
        ),
    },
    {
        "topic": "How this app calculates your footprint",
        "keywords": "how app calculate estimate work method factors algorithm result",
        "answer": (
            "This app multiplies your inputs (travel distance, flights, diet, and "
            "home energy) by published average emission factors to estimate your "
            "annual CO2e, then divides shared home energy across your household. "
            "A machine-learning model rates the result and explains which "
            "categories push it above or below average."
        ),
    },
    {
        "topic": "How to start reducing today",
        "keywords": "start begin first steps easy quick tips reduce today how",
        "answer": (
            "Start with a few high-impact, low-effort changes: switch to a "
            "renewable electricity tariff, eat less red meat, drive and fly less, "
            "and turn your thermostat down a degree. Pick one or two, make them "
            "habits, then build from there."
        ),
    },
    {
        "topic": "Are individual actions worth it",
        "keywords": "individual action worth pointless small difference matter system",
        "answer": (
            "Yes. While systemic change is essential, individual choices reduce "
            "real emissions, save money, shift markets toward cleaner options, "
            "and normalise low-carbon living. Collective individual action adds "
            "up to a significant impact."
        ),
    },
    {
        "topic": "Local and seasonal food",
        "keywords": "local seasonal food miles imported produce buy",
        "answer": (
            "Eating seasonal produce and reducing heavily air-freighted or "
            "hot-housed foods lowers food emissions. That said, what you eat "
            "(plants vs red meat) usually matters more than how far it travelled, "
            "so prioritise diet shifts first."
        ),
    },
    {
        "topic": "Composting",
        "keywords": "compost food scraps garden waste methane reduce",
        "answer": (
            "Composting food and garden waste turns it into useful soil and "
            "avoids the methane released when organic waste rots in landfill. It "
            "is a simple way to cut the footprint of unavoidable food scraps."
        ),
    },
    {
        "topic": "Working from home",
        "keywords": "remote work from home commute office travel hybrid",
        "answer": (
            "Working from home can cut commuting emissions, but the benefit "
            "depends on how you heat and power your home. Maximise the gain by "
            "using efficient heating, a renewable tariff, and avoiding extra car "
            "trips on remote days."
        ),
    },
]
