from datetime import date

from app import db
from app.schemas import IncidentExtraction, ReportFilters

SOURCE = "Fictional demo report"

REPORTS = [
    {
        "original": (
            "LAGOS (fictional) - Marina Crest Hospital in Lagos said on 14 February 2025 that a ransomware attack had "
            "encrypted its patient records system, forcing staff to return to paper files for three days. A group "
            "calling itself GreyLantern demanded 2 million US dollars in bitcoin. The hospital's director, Dr. Tunde "
            "Bakare, said no ransom was paid and that backups were used to restore most systems. The Nigeria Police "
            "Force cybercrime unit has opened an investigation."
        ),
        "english": None,
        "fields": {
            "title": "Ransomware attack disrupts Marina Crest Hospital in Lagos",
            "summary": "A ransomware group called GreyLantern encrypted the patient records of Marina Crest Hospital in Lagos and demanded USD 2 million in bitcoin. The hospital restored systems from backups without paying, and police opened an investigation.",
            "original_language": "en",
            "crime_type": "ransomware",
            "people": ["Tunde Bakare"],
            "organisations": ["Marina Crest Hospital", "GreyLantern", "Nigeria Police Force"],
            "locations": [{"country": "Nigeria", "city": "Lagos"}],
            "incident_date": date(2025, 2, 14),
            "amounts": [{"value": 2000000, "currency": "USD", "context": "ransom demanded in bitcoin"}],
            "confidence": 0.93,
        },
    },
    {
        "original": (
            "ACCRA (fictional) - Kumasi Cocoa Traders lost 380,000 US dollars in September 2024 after criminals "
            "hijacked an email thread with its supplier in Rotterdam and sent new bank details. Finance manager Ama "
            "Owusu approved the transfer on 3 September believing the invoice was genuine. Ghanaian investigators "
            "believe the funds were moved through accounts in two countries within hours."
        ),
        "english": None,
        "fields": {
            "title": "Business email compromise costs Kumasi Cocoa Traders USD 380,000",
            "summary": "Criminals hijacked an email thread between Kumasi Cocoa Traders and its Rotterdam supplier and sent fake bank details. The company transferred USD 380,000 before the fraud was noticed.",
            "original_language": "en",
            "crime_type": "business_email_compromise",
            "people": ["Ama Owusu"],
            "organisations": ["Kumasi Cocoa Traders"],
            "locations": [{"country": "Ghana", "city": "Kumasi"}, {"country": "Netherlands", "city": "Rotterdam"}],
            "incident_date": date(2024, 9, 3),
            "amounts": [{"value": 380000, "currency": "USD", "context": "fraudulent supplier payment"}],
            "confidence": 0.9,
        },
    },
    {
        "original": (
            "ABIDJAN (fictif) - Une vaste campagne d'hameçonnage se faisant passer pour la Direction générale des "
            "impôts a visé des contribuables à Abidjan en mai 2025. Les victimes recevaient un SMS les invitant à "
            "régler une prétendue pénalité sur un faux site. Selon la commissaire Aline Kouassi, plus de 120 "
            "personnes ont été piégées, pour un préjudice total d'environ 60 millions de francs CFA. Le site a été "
            "fermé le 20 mai 2025."
        ),
        "english": (
            "ABIDJAN (fictional) - A large phishing campaign impersonating the Directorate General of Taxes targeted "
            "taxpayers in Abidjan in May 2025. Victims received a text message asking them to pay a supposed penalty on "
            "a fake website. According to Commissioner Aline Kouassi, more than 120 people were caught, with total losses "
            "of about 60 million CFA francs. The site was shut down on 20 May 2025."
        ),
        "fields": {
            "title": "Tax-authority phishing campaign hits Abidjan taxpayers",
            "summary": "A phishing campaign impersonating the tax authority sent text messages directing taxpayers in Abidjan to a fake payment site. More than 120 people lost about XOF 60 million before the site was shut down.",
            "original_language": "fr",
            "crime_type": "phishing",
            "people": ["Aline Kouassi"],
            "organisations": ["Direction générale des impôts"],
            "locations": [{"country": "Côte d'Ivoire", "city": "Abidjan"}],
            "incident_date": date(2025, 5, 20),
            "amounts": [{"value": 60000000, "currency": "XOF", "context": "total victim losses"}],
            "confidence": 0.88,
        },
    },
    {
        "original": (
            "DAKAR (fictif) - Les enquêteurs sénégalais ont démantelé en décembre 2024 un réseau soupçonné d'avoir "
            "blanchi environ 1,5 milliard de francs CFA via des comptes de mobile money ouverts au nom de prête-noms. "
            "L'argent provenait d'escroqueries en ligne et était ensuite transféré vers Bamako, au Mali. Le chef "
            "présumé, Ibrahima Diallo, a été arrêté à Dakar avec quatre complices."
        ),
        "english": (
            "DAKAR (fictional) - Senegalese investigators dismantled a network in December 2024 suspected of laundering "
            "about 1.5 billion CFA francs through mobile money accounts opened in the names of front people. The money "
            "came from online scams and was then transferred to Bamako, Mali. The alleged leader, Ibrahima Diallo, was "
            "arrested in Dakar with four accomplices."
        ),
        "fields": {
            "title": "Mobile money laundering network dismantled in Dakar",
            "summary": "Investigators in Senegal broke up a network that laundered about XOF 1.5 billion of online scam proceeds through mobile money accounts held by front people and moved it to Mali. The alleged leader and four accomplices were arrested.",
            "original_language": "fr",
            "crime_type": "money_laundering",
            "people": ["Ibrahima Diallo"],
            "organisations": [],
            "locations": [{"country": "Senegal", "city": "Dakar"}, {"country": "Mali", "city": "Bamako"}],
            "incident_date": date(2024, 12, 1),
            "amounts": [{"value": 1500000000, "currency": "XOF", "context": "amount laundered"}],
            "confidence": 0.86,
        },
    },
    {
        "original": (
            "VALENCIA (ficticio) - Agentes aduaneros incautaron el 28 de enero de 2025 en el puerto de Valencia 1,2 "
            "toneladas de cocaína ocultas en un contenedor de plátanos procedente de Cartagena, Colombia. El valor "
            "estimado de la droga en el mercado es de 40 millones de euros. La empresa importadora, Frutas del Turia "
            "S.L., afirma no tener relación con el envío. Dos personas fueron detenidas."
        ),
        "english": (
            "VALENCIA (fictional) - Customs officers seized 1.2 tonnes of cocaine hidden in a banana container from "
            "Cartagena, Colombia, at the port of Valencia on 28 January 2025. The estimated street value of the drugs is "
            "40 million euros. The importing company, Frutas del Turia S.L., says it has no connection to the shipment. "
            "Two people were arrested."
        ),
        "fields": {
            "title": "1.2 tonnes of cocaine seized at the port of Valencia",
            "summary": "Customs officers in Valencia found 1.2 tonnes of cocaine in a banana container shipped from Cartagena, Colombia, worth an estimated EUR 40 million. Two people were arrested.",
            "original_language": "es",
            "crime_type": "drug_trafficking",
            "people": [],
            "organisations": ["Frutas del Turia S.L."],
            "locations": [{"country": "Spain", "city": "Valencia"}, {"country": "Colombia", "city": "Cartagena"}],
            "incident_date": date(2025, 1, 28),
            "amounts": [{"value": 40000000, "currency": "EUR", "context": "estimated street value of the cocaine"}],
            "confidence": 0.94,
        },
    },
    {
        "original": (
            "BOGOTÁ (ficticio) - La cadena minorista TiendaNova confirmó el 2 de julio de 2025 una filtración de datos "
            "que expuso nombres, direcciones y números de teléfono de 2,3 millones de clientes. Según la directora de "
            "seguridad, Laura Méndez, los atacantes accedieron a una base de datos de pruebas mal configurada. La "
            "Superintendencia de Industria y Comercio abrió una investigación."
        ),
        "english": (
            "BOGOTÁ (fictional) - Retail chain TiendaNova confirmed on 2 July 2025 a data breach that exposed the names, "
            "addresses and phone numbers of 2.3 million customers. According to security director Laura Méndez, the "
            "attackers accessed a misconfigured test database. The Superintendency of Industry and Commerce opened an "
            "investigation."
        ),
        "fields": {
            "title": "TiendaNova data breach exposes 2.3 million customers in Colombia",
            "summary": "Attackers accessed a misconfigured test database at retailer TiendaNova and exposed personal data of 2.3 million customers. Colombia's Superintendency of Industry and Commerce is investigating.",
            "original_language": "es",
            "crime_type": "data_breach",
            "people": ["Laura Méndez"],
            "organisations": ["TiendaNova", "Superintendencia de Industria y Comercio"],
            "locations": [{"country": "Colombia", "city": "Bogotá"}],
            "incident_date": date(2025, 7, 2),
            "amounts": [],
            "confidence": 0.91,
        },
    },
    {
        "original": (
            "الدار البيضاء (خيالي) - أعلنت السلطات المغربية في 15 أكتوبر 2024 تفكيك شبكة للاتجار بالبشر كانت تستدرج "
            "شابات بوعود عمل وهمية في دبي. وقالت المصادر إن الشبكة كانت تتقاضى من كل ضحية 30 ألف درهم مقابل "
            "\"تأشيرة وعقد عمل\". وتم توقيف ثلاثة أشخاص في الدار البيضاء، من بينهم المدعو كريم العلوي، بينما تم "
            "إنقاذ 14 ضحية."
        ),
        "english": (
            "CASABLANCA (fictional) - Moroccan authorities announced on 15 October 2024 the dismantling of a human "
            "trafficking network that lured young women with fake job offers in Dubai. Sources said the network charged "
            "each victim 30,000 dirhams for a \"visa and work contract\". Three people were arrested in Casablanca, "
            "including one Karim El Alaoui, and 14 victims were rescued."
        ),
        "fields": {
            "title": "Human trafficking network using fake Dubai job offers dismantled in Casablanca",
            "summary": "Moroccan authorities broke up a network that lured young women with fake jobs in Dubai and charged each victim MAD 30,000. Three suspects were arrested and 14 victims rescued.",
            "original_language": "ar",
            "crime_type": "human_trafficking",
            "people": ["Karim El Alaoui"],
            "organisations": [],
            "locations": [{"country": "Morocco", "city": "Casablanca"}, {"country": "United Arab Emirates", "city": "Dubai"}],
            "incident_date": date(2024, 10, 15),
            "amounts": [{"value": 30000, "currency": "MAD", "context": "fee charged to each victim"}],
            "confidence": 0.87,
        },
    },
    {
        "original": (
            "القاهرة (خيالي) - حذّر بنك النيل الرقمي عملاءه في أبريل 2025 من رسائل نصية مزيفة تطلب تحديث بيانات "
            "البطاقة عبر رابط احتيالي. وأفاد البنك بأن المحتالين استولوا على نحو 3.5 مليون جنيه مصري من حسابات "
            "أكثر من 200 عميل في القاهرة والجيزة. وتتابع وحدة مكافحة الجرائم الإلكترونية القضية."
        ),
        "english": (
            "CAIRO (fictional) - Nile Digital Bank warned its customers in April 2025 about fake text messages asking "
            "them to update their card details through a fraudulent link. The bank said the fraudsters took about 3.5 "
            "million Egyptian pounds from the accounts of more than 200 customers in Cairo and Giza. The cybercrime unit "
            "is following the case."
        ),
        "fields": {
            "title": "Fake bank text messages drain EGP 3.5 million from Cairo customers",
            "summary": "Fraudsters sent fake text messages asking Nile Digital Bank customers to update card details on a fraudulent link, taking about EGP 3.5 million from more than 200 accounts in Cairo and Giza.",
            "original_language": "ar",
            "crime_type": "online_fraud",
            "people": [],
            "organisations": ["Nile Digital Bank"],
            "locations": [{"country": "Egypt", "city": "Cairo"}, {"country": "Egypt", "city": "Giza"}],
            "incident_date": date(2025, 4, 1),
            "amounts": [{"value": 3500000, "currency": "EGP", "context": "stolen from customer accounts"}],
            "confidence": 0.85,
        },
    },
]


def seed() -> int:
    db.init_db()
    with db.session() as s:
        if db.search_reports(s, ReportFilters(), limit=1):
            print("Reports already exist, skipping seed.")
            return 0
        for r in REPORTS:
            extraction = IncidentExtraction.model_validate(r["fields"])
            db.save_report(s, extraction, r["original"], r["english"] or r["original"], SOURCE)
    print(f"Seeded {len(REPORTS)} fictional demo reports.")
    return len(REPORTS)


if __name__ == "__main__":
    seed()
