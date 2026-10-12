from __future__ import annotations

from typing import Dict, List, Any

# Canonical world-location data for EnejiStats.
#
# Country identity:
#   * ISO 3166-1 alpha-2 is authoritative for the 249 ISO entries.
#   * XK/Kosovo is retained as an explicit user-assigned compatibility extension
#     because the existing EnejiStats geographic grouping already used XK.
#
# Administrative hierarchy:
#   country -> region/state/province/etc. -> subregion/LGA/county/district/etc.
#
# The location API is intentionally kept in location_module.py. This file is
# pure data and validation only, so it cannot create a circular route import.

from typing import Dict, List, Any

# ── CountryLocationConfig ─────────────────────────────────────────────────────
class CountryLocationConfig:
    def __init__(self, region_label: str, subregion_label: str, regions: Any, subregions: Any = None):
        self.region_label = region_label
        self.subregion_label = subregion_label
        self.regions = regions
        self.subregions = subregions if subregions is not None else {}


# ── Country display names (ISO 3166-1 alpha-2) ────────────────────────────────
COUNTRY_NAMES: Dict[str, str] = {
    "AF": "Afghanistan",
    "AL": "Albania",
    "DZ": "Algeria",
    "AD": "Andorra",
    "AO": "Angola",
    "AG": "Antigua and Barbuda",
    "AR": "Argentina",
    "AM": "Armenia",
    "AU": "Australia",
    "AT": "Austria",
    "AZ": "Azerbaijan",
    "BS": "Bahamas",
    "BH": "Bahrain",
    "BD": "Bangladesh",
    "BB": "Barbados",
    "BY": "Belarus",
    "BE": "Belgium",
    "BZ": "Belize",
    "BJ": "Benin",
    "BT": "Bhutan",
    "BO": "Bolivia",
    "BA": "Bosnia and Herzegovina",
    "BW": "Botswana",
    "BR": "Brazil",
    "BN": "Brunei",
    "BG": "Bulgaria",
    "BF": "Burkina Faso",
    "BI": "Burundi",
    "CV": "Cabo Verde",
    "KH": "Cambodia",
    "CM": "Cameroon",
    "CA": "Canada",
    "CF": "Central African Republic",
    "TD": "Chad",
    "CL": "Chile",
    "CN": "China",
    "CO": "Colombia",
    "KM": "Comoros",
    "CG": "Congo",
    "CD": "Democratic Republic of the Congo",
    "CR": "Costa Rica",
    "CI": "Côte d'Ivoire",
    "HR": "Croatia",
    "CU": "Cuba",
    "CY": "Cyprus",
    "CZ": "Czech Republic",
    "DK": "Denmark",
    "DJ": "Djibouti",
    "DM": "Dominica",
    "DO": "Dominican Republic",
    "EC": "Ecuador",
    "EG": "Egypt",
    "SV": "El Salvador",
    "GQ": "Equatorial Guinea",
    "ER": "Eritrea",
    "EE": "Estonia",
    "SZ": "Eswatini",
    "ET": "Ethiopia",
    "FJ": "Fiji",
    "FI": "Finland",
    "FR": "France",
    "GA": "Gabon",
    "GM": "Gambia",
    "GE": "Georgia",
    "DE": "Germany",
    "GH": "Ghana",
    "GR": "Greece",
    "GD": "Grenada",
    "GT": "Guatemala",
    "GN": "Guinea",
    "GW": "Guinea-Bissau",
    "GY": "Guyana",
    "HT": "Haiti",
    "HN": "Honduras",
    "HU": "Hungary",
    "IS": "Iceland",
    "IN": "India",
    "ID": "Indonesia",
    "IR": "Iran",
    "IQ": "Iraq",
    "IE": "Ireland",
    "IL": "Israel",
    "IT": "Italy",
    "JM": "Jamaica",
    "JP": "Japan",
    "JO": "Jordan",
    "KZ": "Kazakhstan",
    "KE": "Kenya",
    "KI": "Kiribati",
    "KP": "North Korea",
    "KR": "South Korea",
    "KW": "Kuwait",
    "KG": "Kyrgyzstan",
    "LA": "Laos",
    "LV": "Latvia",
    "LB": "Lebanon",
    "LS": "Lesotho",
    "LR": "Liberia",
    "LY": "Libya",
    "LI": "Liechtenstein",
    "LT": "Lithuania",
    "LU": "Luxembourg",
    "MG": "Madagascar",
    "MW": "Malawi",
    "MY": "Malaysia",
    "MV": "Maldives",
    "ML": "Mali",
    "MT": "Malta",
    "MH": "Marshall Islands",
    "MR": "Mauritania",
    "MU": "Mauritius",
    "MX": "Mexico",
    "FM": "Micronesia",
    "MD": "Moldova",
    "MC": "Monaco",
    "MN": "Mongolia",
    "ME": "Montenegro",
    "MA": "Morocco",
    "MZ": "Mozambique",
    "MM": "Myanmar",
    "NA": "Namibia",
    "NR": "Nauru",
    "NP": "Nepal",
    "NL": "Netherlands",
    "NZ": "New Zealand",
    "NI": "Nicaragua",
    "NE": "Niger",
    "NG": "Nigeria",
    "MK": "North Macedonia",
    "NO": "Norway",
    "OM": "Oman",
    "PK": "Pakistan",
    "PW": "Palau",
    "PS": "Palestine",
    "PA": "Panama",
    "PG": "Papua New Guinea",
    "PY": "Paraguay",
    "PE": "Peru",
    "PH": "Philippines",
    "PL": "Poland",
    "PT": "Portugal",
    "QA": "Qatar",
    "RO": "Romania",
    "RU": "Russia",
    "RW": "Rwanda",
    "KN": "Saint Kitts and Nevis",
    "LC": "Saint Lucia",
    "VC": "Saint Vincent and the Grenadines",
    "WS": "Samoa",
    "SM": "San Marino",
    "ST": "São Tomé and Príncipe",
    "SA": "Saudi Arabia",
    "SN": "Senegal",
    "RS": "Serbia",
    "SC": "Seychelles",
    "SL": "Sierra Leone",
    "SG": "Singapore",
    "SK": "Slovakia",
    "SI": "Slovenia",
    "SB": "Solomon Islands",
    "SO": "Somalia",
    "ZA": "South Africa",
    "SS": "South Sudan",
    "ES": "Spain",
    "LK": "Sri Lanka",
    "SD": "Sudan",
    "SR": "Suriname",
    "SE": "Sweden",
    "CH": "Switzerland",
    "SY": "Syria",
    "TW": "Taiwan",
    "TJ": "Tajikistan",
    "TZ": "Tanzania",
    "TH": "Thailand",
    "TL": "Timor-Leste",
    "TG": "Togo",
    "TO": "Tonga",
    "TT": "Trinidad and Tobago",
    "TN": "Tunisia",
    "TR": "Türkiye",
    "TM": "Turkmenistan",
    "TV": "Tuvalu",
    "UG": "Uganda",
    "UA": "Ukraine",
    "AE": "United Arab Emirates",
    "GB": "United Kingdom",
    "US": "United States",
    "UY": "Uruguay",
    "UZ": "Uzbekistan",
    "VU": "Vanuatu",
    "VA": "Vatican City",
    "VE": "Venezuela",
    "VN": "Vietnam",
    "YE": "Yemen",
    "ZM": "Zambia",
    "ZW": "Zimbabwe",
}

# ── Existing constants (Nigeria, US, Canada, GB, UAE, India, Ghana, Kenya, ────
# ── South Africa, France, Spain, Italy, Germany, Netherlands, Belgium, ────────
# ── Portugal, Switzerland) are defined elsewhere in the original file. ─────────



# ── Legacy EnejiStats location constants ─────────────────────────────────────
NIGERIAN_STATES: List[str] = [
    "Abia", "Adamawa", "Akwa Ibom", "Anambra", "Bauchi", "Bayelsa", "Benue",
    "Borno", "Cross River", "Delta", "Ebonyi", "Edo", "Ekiti", "Enugu",
    "Federal Capital Territory", "Gombe", "Imo", "Jigawa", "Kaduna", "Kano",
    "Katsina", "Kebbi", "Kogi", "Kwara", "Lagos", "Nasarawa", "Niger",
    "Ogun", "Ondo", "Osun", "Oyo", "Plateau", "Rivers", "Sokoto", "Taraba",
    "Yobe", "Zamfara",
]

NIGERIAN_LGAS: Dict[str, List[str]] = {
    "Abia": [
        "Aba North", "Aba South", "Arochukwu", "Bende", "Ikwuano",
        "Isiala Ngwa North", "Isiala Ngwa South", "Isuikwuato", "Obi Ngwa",
        "Ohafia", "Osisioma", "Ugwunagbo", "Ukwa East", "Ukwa West",
        "Umuahia North", "Umuahia South", "Umu Nneochi",
    ],
    "Adamawa": [
        "Demsa", "Fufure", "Ganye", "Girei", "Gombi", "Guyuk", "Hong",
        "Jada", "Lamurde", "Madagali", "Maiha", "Mayo Belwa", "Michika",
        "Mubi North", "Mubi South", "Numan", "Shelleng", "Song", "Toungo",
        "Yola North", "Yola South",
    ],
    "Akwa Ibom": [
        "Abak", "Eastern Obolo", "Eket", "Esit Eket", "Essien Udim",
        "Etim Ekpo", "Etinan", "Ibeno", "Ibesikpo Asutan", "Ibiono Ibom",
        "Ika", "Ikono", "Ikot Abasi", "Ikot Ekpene", "Ini", "Itu", "Mbo",
        "Mkpat Enin", "Nsit Atai", "Nsit Ibom", "Nsit Ubium", "Obot Akara",
        "Okobo", "Onna", "Oron", "Oruk Anam", "Udung Uko", "Ukanafun",
        "Uruan", "Urue-Offong/Oruko", "Uyo",
    ],
    "Anambra": [
        "Aguata", "Anambra East", "Anambra West", "Anaocha", "Awka North",
        "Awka South", "Ayamelum", "Dunukofia", "Ekwusigo", "Idemili North",
        "Idemili South", "Ihiala", "Njikoka", "Nnewi North", "Nnewi South",
        "Ogbaru", "Onitsha North", "Onitsha South", "Orumba North",
        "Orumba South", "Oyi",
    ],
    "Bauchi": [
        "Alkaleri", "Bauchi", "Bogoro", "Damban", "Darazo", "Dass",
        "Gamawa", "Ganjuwa", "Giade", "Itas/Gadau", "Jama'are", "Katagum",
        "Kirfi", "Misau", "Ningi", "Shira", "Tafawa Balewa", "Toro",
        "Warji", "Zaki",
    ],
    "Bayelsa": [
        "Brass", "Ekeremor", "Kolokuma/Opokuma", "Nembe", "Ogbia",
        "Sagbama", "Southern Ijaw", "Yenagoa",
    ],
    "Benue": [
        "Ado", "Agatu", "Apa", "Buruku", "Gboko", "Guma", "Gwer East",
        "Gwer West", "Katsina-Ala", "Konshisha", "Kwande", "Logo",
        "Makurdi", "Obi", "Ogbadibo", "Ohimini", "Oju", "Okpokwu", "Otukpo",
        "Tarka", "Ukum", "Ushongo", "Vandeikya",
    ],
    "Borno": [
        "Abadam", "Askira/Uba", "Bama", "Bayo", "Biu", "Chibok", "Damboa",
        "Dikwa", "Gubio", "Guzamala", "Gwoza", "Hawul", "Jere", "Kaga",
        "Kala/Balge", "Konduga", "Kukawa", "Kwaya Kusar", "Mafa",
        "Magumeri", "Maiduguri", "Marte", "Mobbar", "Monguno", "Ngala",
        "Nganzai", "Shani",
    ],
    "Cross River": [
        "Abi", "Akamkpa", "Akpabuyo", "Bakassi", "Bekwarra", "Biase",
        "Boki", "Calabar Municipal", "Calabar South", "Etung", "Ikom",
        "Obanliku", "Obubra", "Obudu", "Odukpani", "Ogoja", "Yakurr",
        "Yala",
    ],
    "Delta": [
        "Aniocha North", "Aniocha South", "Bomadi", "Burutu",
        "Ethiope East", "Ethiope West", "Ika North East", "Ika South",
        "Isoko North", "Isoko South", "Ndokwa East", "Ndokwa West", "Okpe",
        "Oshimili North", "Oshimili South", "Patani", "Sapele", "Udu",
        "Ughelli North", "Ughelli South", "Ukwuani", "Uvwie", "Warri North",
        "Warri South", "Warri South West",
    ],
    "Ebonyi": [
        "Abakaliki", "Afikpo North", "Afikpo South", "Ebonyi", "Ezza North",
        "Ezza South", "Ikwo", "Ishielu", "Ivo", "Izzi", "Ohaozara",
        "Ohaukwu", "Onicha",
    ],
    "Edo": [
        "Akoko-Edo", "Egor", "Esan Central", "Esan North-East",
        "Esan South-East", "Esan West", "Etsako Central", "Etsako East",
        "Etsako West", "Igueben", "Ikpoba Okha", "Orhionmwon", "Oredo",
        "Ovia North-East", "Ovia South-West", "Owan East", "Owan West",
        "Uhunmwonde",
    ],
    "Ekiti": [
        "Ado Ekiti", "Efon", "Ekiti East", "Ekiti South-West", "Ekiti West",
        "Emure", "Gbonyin", "Ido Osi", "Ijero", "Ikere", "Ikole",
        "Ilejemeje", "Irepodun/Ifelodun", "Ise/Orun", "Moba", "Oye",
    ],
    "Enugu": [
        "Aninri", "Awgu", "Enugu East", "Enugu North", "Enugu South",
        "Ezeagu", "Igbo Etiti", "Igbo Eze North", "Igbo Eze South",
        "Isi Uzo", "Nkanu East", "Nkanu West", "Nsukka", "Oji River",
        "Udenu", "Udi", "Uzo Uwani",
    ],
    "Federal Capital Territory": [
        "Abaji", "Abuja Municipal", "Bwari", "Gwagwalada", "Kuje", "Kwali",
    ],
    "Gombe": [
        "Akko", "Balanga", "Billiri", "Dukku", "Funakaye", "Gombe",
        "Kaltungo", "Kwami", "Nafada", "Shongom", "Yamaltu/Deba",
    ],
    "Imo": [
        "Aboh Mbaise", "Ahiazu Mbaise", "Ehime Mbano", "Ezinihitte",
        "Ideato North", "Ideato South", "Ihitte/Uboma", "Ikeduru",
        "Isiala Mbano", "Isu", "Mbaitoli", "Ngor Okpala", "Njaba",
        "Nkwerre", "Nwangele", "Obowo", "Oguta", "Ohaji/Egbema", "Okigwe",
        "Onuimo", "Orlu", "Orsu", "Oru East", "Oru West", "Owerri Municipal",
        "Owerri North", "Owerri West",
    ],
    "Jigawa": [
        "Auyo", "Babura", "Biriniwa", "Birnin Kudu", "Buji", "Dutse",
        "Gagarawa", "Garki", "Gumel", "Guri", "Gwaram", "Gwiwa", "Hadejia",
        "Jahun", "Kafin Hausa", "Kaugama", "Kazaure", "Kiri Kasama",
        "Kiyawa", "Maigatari", "Malam Madori", "Miga", "Ringim", "Roni",
        "Sule Tankarkar", "Taura", "Yankwashi",
    ],
    "Kaduna": [
        "Birnin Gwari", "Chikun", "Giwa", "Igabi", "Ikara", "Jaba",
        "Jema'a", "Kachia", "Kaduna North", "Kaduna South", "Kagarko",
        "Kajuru", "Kaura", "Kauru", "Kubau", "Kudan", "Lere", "Makarfi",
        "Sabon Gari", "Sanga", "Soba", "Zangon Kataf", "Zaria",
    ],
    "Kano": [
        "Ajingi", "Albasu", "Bagwai", "Bebeji", "Bichi", "Bunkure", "Dala",
        "Dambatta", "Dawakin Kudu", "Dawakin Tofa", "Doguwa", "Fagge",
        "Gabasawa", "Garko", "Garun Mallam", "Gaya", "Gezawa", "Gwale",
        "Gwarzo", "Kabo", "Kano Municipal", "Karaye", "Kibiya", "Kiru",
        "Kumbotso", "Kunchi", "Kura", "Madobi", "Makoda", "Minjibir",
        "Nasarawa", "Rano", "Rimin Gado", "Rogo", "Shanono", "Sumaila",
        "Takai", "Tarauni", "Tofa", "Tsanyawa", "Tudun Wada", "Ungogo",
        "Warawa", "Wudil",
    ],
    "Katsina": [
        "Bakori", "Batagarawa", "Batsari", "Baure", "Bindawa", "Charanchi",
        "Dandume", "Danja", "Dan Musa", "Daura", "Dutsi", "Dutsin Ma",
        "Faskari", "Funtua", "Ingawa", "Jibia", "Kafur", "Kaita", "Kankara",
        "Kankia", "Katsina", "Kurfi", "Kusada", "Mai'Adua", "Malumfashi",
        "Mani", "Mashi", "Matazu", "Musawa", "Rimi", "Sabuwa", "Safana",
        "Sandamu", "Zango",
    ],
    "Kebbi": [
        "Aleiro", "Arewa Dandi", "Argungu", "Augie", "Bagudo",
        "Birnin Kebbi", "Bunza", "Dandi", "Fakai", "Gwandu", "Jega",
        "Kalgo", "Koko/Besse", "Maiyama", "Ngaski", "Sakaba", "Shanga",
        "Suru", "Wasagu/Danko", "Yauri", "Zuru",
    ],
    "Kogi": [
        "Adavi", "Ajaokuta", "Ankpa", "Bassa", "Dekina", "Ibaji", "Idah",
        "Igalamela Odolu", "Ijumu", "Kabba/Bunu", "Kogi", "Lokoja",
        "Mopa Muro", "Ofu", "Ogori/Magongo", "Okehi", "Okene", "Olamaboro",
        "Omala", "Yagba East", "Yagba West",
    ],
    "Kwara": [
        "Asa", "Baruten", "Edu", "Ekiti", "Ifelodun", "Ilorin East",
        "Ilorin South", "Ilorin West", "Irepodun", "Isin", "Kaiama",
        "Moro", "Offa", "Oke Ero", "Oyun", "Pategi",
    ],
    "Lagos": [
        "Agege", "Ajeromi-Ifelodun", "Alimosho", "Amuwo-Odofin", "Apapa",
        "Badagry", "Epe", "Eti Osa", "Ibeju-Lekki", "Ifako-Ijaiye",
        "Ikeja", "Ikorodu", "Kosofe", "Lagos Island", "Lagos Mainland",
        "Mushin", "Ojo", "Oshodi-Isolo", "Shomolu", "Surulere",
    ],
    "Nasarawa": [
        "Akwanga", "Awe", "Doma", "Karu", "Keana", "Keffi", "Kokona",
        "Lafia", "Nasarawa", "Nasarawa Egon", "Obi", "Toto", "Wamba",
    ],
    "Niger": [
        "Agaie", "Agwara", "Bida", "Borgu", "Bosso", "Chanchaga", "Edati",
        "Gbako", "Gurara", "Katcha", "Kontagora", "Lapai", "Lavun",
        "Magama", "Mariga", "Mashegu", "Mokwa", "Moya", "Paikoro", "Rafi",
        "Rijau", "Shiroro", "Suleja", "Tafa", "Wushishi",
    ],
    "Ogun": [
        "Abeokuta North", "Abeokuta South", "Ado-Odo/Ota",
        "Egbado North (Yewa North)", "Egbado South (Yewa South)",
        "Ewekoro", "Ifo", "Ijebu East", "Ijebu North", "Ijebu North East",
        "Ijebu Ode", "Ikenne", "Imeko Afon", "Ipokia", "Obafemi Owode",
        "Odeda", "Odogbolu", "Ogun Waterside", "Remo North", "Shagamu",
    ],
    "Ondo": [
        "Akoko North-East", "Akoko North-West", "Akoko South-East",
        "Akoko South-West", "Akure North", "Akure South", "Ese Odo",
        "Idanre", "Ifedore", "Ilaje", "Ile Oluji/Okeigbo", "Irele",
        "Odigbo", "Okitipupa", "Ondo East", "Ondo West", "Ose", "Owo",
    ],
    "Osun": [
        "Aiyedaade", "Aiyedire", "Atakunmosa East", "Atakunmosa West",
        "Boluwaduro", "Boripe", "Ede North", "Ede South", "Egbedore",
        "Ejigbo", "Ife Central", "Ife East", "Ife North", "Ife South",
        "Ifedayo", "Ifelodun", "Ila", "Ilesa East", "Ilesa West",
        "Irepodun", "Irewole", "Isokan", "Iwo", "Obokun", "Odo Otin",
        "Ola Oluwa", "Olorunda", "Oriade", "Orolu", "Osogbo",
    ],
    "Oyo": [
        "Afijio", "Akinyele", "Atiba", "Atisbo", "Egbeda", "Ibadan North",
        "Ibadan North-East", "Ibadan North-West", "Ibadan South-East",
        "Ibadan South-West", "Ibarapa Central", "Ibarapa East",
        "Ibarapa North", "Ido", "Irepo", "Iseyin", "Itesiwaju", "Iwajowa",
        "Kajola", "Lagelu", "Ogbomosho North", "Ogbomosho South",
        "Ogo Oluwa", "Olorunsogo", "Oluyole", "Ona Ara", "Orelope",
        "Ori Ire", "Oyo East", "Oyo West", "Saki East", "Saki West",
        "Surulere",
    ],
    "Plateau": [
        "Bokkos", "Barkin Ladi", "Bassa", "Jos East", "Jos North",
        "Jos South", "Kanam", "Kanke", "Langtang North", "Langtang South",
        "Mangu", "Mikang", "Pankshin", "Qua'an Pan", "Riyom", "Shendam",
        "Wase",
    ],
    "Rivers": [
        "Abua/Odual", "Ahoada East", "Ahoada West", "Akuku-Toru", "Andoni",
        "Asari-Toru", "Bonny", "Degema", "Eleme", "Emuoha", "Etche",
        "Gokana", "Ikwerre", "Khana", "Obio/Akpor", "Ogba/Egbema/Ndoni",
        "Ogu/Bolo", "Okrika", "Omuma", "Opobo/Nkoro", "Oyigbo",
        "Port Harcourt", "Tai",
    ],
    "Sokoto": [
        "Binji", "Bodinga", "Dange Shuni", "Gada", "Goronyo", "Gudu",
        "Gwadabawa", "Illela", "Isa", "Kebbe", "Kware", "Rabah",
        "Sabon Birni", "Shagari", "Silame", "Sokoto North", "Sokoto South",
        "Tambuwal", "Tangaza", "Tureta", "Wamako", "Wurno", "Yabo",
    ],
    "Taraba": [
        "Ardo Kola", "Bali", "Donga", "Gashaka", "Gassol", "Ibi", "Jalingo",
        "Karim Lamido", "Kumi", "Lau", "Sardauna", "Takum", "Ussa",
        "Wukari", "Yorro", "Zing",
    ],
    "Yobe": [
        "Bade", "Bursari", "Damaturu", "Fika", "Fune", "Geidam", "Gujba",
        "Gulani", "Jakusko", "Karasuwa", "Machina", "Nangere", "Nguru",
        "Potiskum", "Tarmuwa", "Yunusari", "Yusufari",
    ],
    "Zamfara": [
        "Anka", "Bakura", "Birnin Magaji/Kiyaw", "Bukkuyum", "Bungudu",
        "Gummi", "Gusau", "Kaura Namoda", "Maradun", "Maru",
        "Shinkafi", "Talata Mafara", "Tsafe", "Zurmi",
    ],
}

_missing_lga_lists = [s for s in NIGERIAN_STATES if s not in NIGERIAN_LGAS]
_orphaned_lga_lists = [s for s in NIGERIAN_LGAS if s not in NIGERIAN_STATES]
if _missing_lga_lists or _orphaned_lga_lists:
    raise RuntimeError(
        "Nigeria location data is inconsistent. "
        f"States missing LGA lists: {_missing_lga_lists}; "
        f"LGA lists without a matching state: {_orphaned_lga_lists}"
    )


US_STATES: List[str] = [
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado",
    "Connecticut", "Delaware", "Florida", "Georgia", "Hawaii", "Idaho",
    "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana",
    "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota",
    "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada",
    "New Hampshire", "New Jersey", "New Mexico", "New York",
    "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon",
    "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota",
    "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington",
    "West Virginia", "Wisconsin", "Wyoming",
]

US_COUNTIES: Dict[str, List[str]] = {
    "California": [
        "Los Angeles County", "Orange County", "San Diego County",
        "San Francisco County", "Alameda County", "Sacramento County",
    ],
    "New York": [
        "New York County", "Kings County", "Queens County",
        "Bronx County", "Richmond County", "Suffolk County",
    ],
    "Texas": [
        "Harris County", "Dallas County", "Travis County",
        "Bexar County", "Tarrant County", "Collin County",
    ],
    "Florida": [
        "Miami-Dade County", "Broward County", "Orange County",
        "Palm Beach County", "Hillsborough County",
    ],
    "Illinois": ["Cook County", "DuPage County", "Lake County"],
}

CANADA_PROVINCES: List[str] = [
    "Alberta", "British Columbia", "Manitoba", "New Brunswick",
    "Newfoundland and Labrador", "Northwest Territories", "Nova Scotia",
    "Nunavut", "Ontario", "Prince Edward Island", "Quebec",
    "Saskatchewan", "Yukon",
]

CANADA_CITIES: Dict[str, List[str]] = {
    "Ontario": ["Toronto", "Ottawa", "Mississauga", "Hamilton", "London"],
    "British Columbia": ["Vancouver", "Victoria", "Surrey", "Burnaby"],
    "Quebec": ["Montreal", "Quebec City", "Laval", "Gatineau"],
    "Alberta": ["Calgary", "Edmonton", "Red Deer"],
}

UK_COUNTRIES: List[str] = ["England", "Scotland", "Wales", "Northern Ireland"]

UK_DISTRICTS: Dict[str, List[str]] = {
    "England": ["Greater London", "Greater Manchester", "West Midlands",
                "West Yorkshire", "Merseyside"],
    "Scotland": ["Glasgow City", "City of Edinburgh", "Aberdeen City"],
    "Wales": ["Cardiff", "Swansea", "Newport"],
    "Northern Ireland": ["Belfast", "Derry and Strabane"],
}

UAE_EMIRATES: List[str] = [
    "Abu Dhabi", "Dubai", "Sharjah", "Ajman", "Umm Al Quwain",
    "Ras Al Khaimah", "Fujairah",
]

INDIA_STATES: List[str] = [
    "Andhra Pradesh", "Bihar", "Delhi", "Gujarat", "Karnataka", "Kerala",
    "Maharashtra", "Punjab", "Rajasthan", "Tamil Nadu", "Uttar Pradesh",
    "West Bengal",
]
INDIA_DISTRICTS: Dict[str, List[str]] = {
    "Maharashtra": ["Mumbai City", "Pune", "Nagpur", "Nashik"],
    "Karnataka": ["Bengaluru Urban", "Mysuru", "Mangaluru"],
    "Delhi": ["New Delhi", "North Delhi", "South Delhi"],
}

GHANA_REGIONS: List[str] = ["Greater Accra", "Ashanti", "Western"]

KENYA_COUNTIES: List[str] = ["Nairobi", "Mombasa", "Kisumu"]

SOUTH_AFRICA_PROVINCES: List[str] = ["Gauteng", "Western Cape", "KwaZulu-Natal"]


FRANCE_REGIONS: List[str] = [
    "Île-de-France", "Provence-Alpes-Côte d'Azur", "Auvergne-Rhône-Alpes",
]

SPAIN_REGIONS: List[str] = ["Madrid", "Catalonia", "Andalusia"]

ITALY_REGIONS: List[str] = ["Lombardy", "Lazio", "Sicily"]

GERMANY_REGIONS: List[str] = ["Bavaria", "Berlin", "North Rhine-Westphalia"]

NETHERLANDS_REGIONS: List[str] = ["North Holland", "South Holland", "Utrecht"]

BELGIUM_REGIONS: List[str] = ["Flanders", "Wallonia", "Brussels-Capital"]

PORTUGAL_REGIONS: List[str] = ["Lisbon", "Porto", "Braga"]

SWITZERLAND_REGIONS: List[str] = ["Zürich", "Geneva", "Bern"]

# ── Country display names (ISO 3166-1 alpha-2) ────────────────────────────────


# ── Expanded country constants from the supplied world-location dataset ───────
# ══════════════════════════════════════════════════════════════════════════════
# NEW COUNTRY CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════

# ── Afghanistan ───────────────────────────────────────────────────────────────
AFGHANISTAN_PROVINCES: List[str] = [
    "Kabul", "Herat", "Kandahar", "Balkh", "Nangarhar", "Kunduz", "Ghazni",
    "Badakhshan", "Takhar", "Baghlan", "Wardak", "Logar", "Paktia", "Khost",
    "Laghman", "Kunar", "Nuristan", "Kapisa", "Parwan", "Bamyan", "Daikundi",
    "Ghor", "Farah", "Nimroz", "Helmand", "Zabul", "Uruzgan", "Paktika",
    "Samangan", "Jawzjan", "Sar-e Pol", "Faryab", "Badghis",
    "Sari Pul", "Daykundi",
]
AFGHANISTAN_DISTRICTS: Dict[str, List[str]] = {
    "Kabul": ["Kabul City", "Bagram", "Mir Bacha Kot", "Deh Sabz", "Khaki Jabbar"],
    "Herat": ["Herat City", "Guzara", "Injil", "Pashtun Zarghun", "Adraskan"],
    "Kandahar": ["Kandahar City", "Arghandab", "Spin Boldak", "Panjwai", "Daman"],
    "Balkh": ["Mazar-i-Sharif", "Dehdadi", "Nahr-e Shahi", "Dawlatabad", "Khulm"],
    "Nangarhar": ["Jalalabad", "Behsud", "Rodat", "Kama", "Surkhrod"],
}

# ── Albania ───────────────────────────────────────────────────────────────────
ALBANIA_COUNTIES: List[str] = [
    "Berat", "Dibër", "Durrës", "Elbasan", "Fier", "Gjirokastër",
    "Korçë", "Kukës", "Lezhë", "Shkodër", "Tiranë", "Vlorë",
]
ALBANIA_MUNICIPALITIES: Dict[str, List[str]] = {
    "Tiranë": ["Tirana", "Kamëz", "Kashar", "Paskuqan", "Vora"],
    "Durrës": ["Durrës City", "Krujë", "Shijak", "Kavajë"],
    "Vlorë": ["Vlorë City", "Sarandë", "Himarë", "Selenicë"],
    "Shkodër": ["Shkodër City", "Lezhë City", "Laç"],
    "Fier": ["Fier City", "Lushnjë", "Berat City", "Kuçovë"],
}

# ── Andorra ───────────────────────────────────────────────────────────────────
ANDORRA_PARISHES: List[str] = [
    "Andorra la Vella", "Canillo", "Encamp", "Escaldes-Engordany",
    "La Massana", "Ordino", "Sant Julià de Lòria",
]
ANDORRA_COMMUNES: Dict[str, List[str]] = {
    "Andorra la Vella": ["Andorra la Vella City"],
    "Escaldes-Engordany": ["Escaldes", "Engordany"],
    "Encamp": ["Encamp Village", "Canillo Village"],
    "La Massana": ["La Massana Village", "Ordino Village"],
    "Sant Julià de Lòria": ["Sant Julià de Lòria Village"],
}

# ── Antigua and Barbuda ───────────────────────────────────────────────────────
ANTIGUA_BARBUDA_PARISHES: List[str] = [
    "Saint George", "Saint John", "Saint Mary", "Saint Paul",
    "Saint Peter", "Saint Philip", "Barbuda", "Redonda",
]
ANTIGUA_BARBUDA_VILLAGES: Dict[str, List[str]] = {
    "Saint John": ["Saint John's City", "Falmouth", "All Saints"],
    "Saint George": ["Liberta", "Swetes", "Freetown"],
    "Saint Mary": ["Old Road", "Bolans", "Jennings"],
    "Barbuda": ["Codrington"],
}

# ── Argentina ─────────────────────────────────────────────────────────────────
ARGENTINA_PROVINCES: List[str] = [
    "Buenos Aires", "Catamarca", "Chaco", "Chubut", "Córdoba",
    "Corrientes", "Entre Ríos", "Formosa", "Jujuy", "La Pampa",
    "La Rioja", "Mendoza", "Misiones", "Neuquén", "Río Negro",
    "Salta", "San Juan", "San Luis", "Santa Cruz", "Santa Fe",
    "Santiago del Estero", "Tierra del Fuego", "Tucumán",
    "Ciudad Autónoma de Buenos Aires",
]
ARGENTINA_DEPARTMENTS: Dict[str, List[str]] = {
    "Buenos Aires": ["La Plata", "Mar del Plata", "Quilmes", "Lomas de Zamora", "Lanús"],
    "Córdoba": ["Córdoba Capital", "Villa María", "Río Cuarto", "San Francisco"],
    "Santa Fe": ["Rosario", "Santa Fe City", "Rafaela", "Venado Tuerto"],
    "Mendoza": ["Mendoza Capital", "San Rafael", "Luján de Cuyo", "Godoy Cruz"],
    "Tucumán": ["San Miguel de Tucumán", "Concepción", "Tafí Viejo"],
}

# ── Armenia ───────────────────────────────────────────────────────────────────
ARMENIA_PROVINCES: List[str] = [
    "Aragatsotn", "Ararat", "Armavir", "Gegharkunik", "Kotayk",
    "Lori", "Shirak", "Syunik", "Tavush", "Vayots Dzor", "Yerevan",
]
ARMENIA_COMMUNITIES: Dict[str, List[str]] = {
    "Yerevan": ["Yerevan City", "Abovyan", "Charentsavan"],
    "Kotayk": ["Hrazdan", "Abovyan", "Kotayk", "Charentsavan"],
    "Ararat": ["Artashat", "Masis", "Vedi"],
    "Lori": ["Vanadzor", "Alaverdi", "Stepanavan"],
    "Shirak": ["Gyumri", "Artik"],
}

# ── Australia ─────────────────────────────────────────────────────────────────
AUSTRALIA_STATES: List[str] = [
    "New South Wales", "Victoria", "Queensland", "Western Australia",
    "South Australia", "Tasmania", "Australian Capital Territory",
    "Northern Territory",
]
AUSTRALIA_LOCAL_GOVERNMENTS: Dict[str, List[str]] = {
    "New South Wales": ["Sydney", "Newcastle", "Wollongong", "Central Coast", "Blue Mountains"],
    "Victoria": ["Melbourne", "Geelong", "Ballarat", "Bendigo", "Shepparton"],
    "Queensland": ["Brisbane", "Gold Coast", "Sunshine Coast", "Townsville", "Cairns"],
    "Western Australia": ["Perth", "Fremantle", "Joondalup", "Stirling", "Mandurah"],
    "South Australia": ["Adelaide", "Mount Gambier", "Whyalla", "Murray Bridge"],
    "Tasmania": ["Hobart", "Launceston", "Devonport", "Burnie"],
    "Australian Capital Territory": ["Canberra", "Tuggeranong", "Belconnen", "Woden"],
    "Northern Territory": ["Darwin", "Alice Springs", "Palmerston", "Katherine"],
}

# ── Austria ───────────────────────────────────────────────────────────────────
AUSTRIA_STATES: List[str] = [
    "Burgenland", "Carinthia", "Lower Austria", "Upper Austria",
    "Salzburg", "Styria", "Tyrol", "Vorarlberg", "Vienna",
]
AUSTRIA_DISTRICTS: Dict[str, List[str]] = {
    "Vienna": ["Vienna City"],
    "Lower Austria": ["St. Pölten", "Krems", "Baden", "Mödling", "Wiener Neustadt"],
    "Upper Austria": ["Linz", "Wels", "Steyr", "Traun", "Leonding"],
    "Styria": ["Graz", "Leoben", "Klagenfurt", "Villach"],
    "Salzburg": ["Salzburg City", "Hallein", "Salzburg-Umgebung"],
    "Tyrol": ["Innsbruck", "Kufstein", "Schwaz", "Kitzbühel"],
    "Carinthia": ["Klagenfurt", "Villach", "Wolfsberg"],
    "Vorarlberg": ["Bregenz", "Dornbirn", "Feldkirch", "Bludenz"],
    "Burgenland": ["Eisenstadt", "Neusiedl am See", "Mattersburg"],
}

# ── Azerbaijan ────────────────────────────────────────────────────────────────
AZERBAIJAN_DISTRICTS: List[str] = [
    "Absheron", "Agdam", "Agdash", "Aghjabadi", "Agstafa",
    "Agsu", "Astara", "Balakan", "Barda", "Beylagan",
    "Bilasuvar", "Dashkasan", "Fizuli", "Gadabay", "Goranboy",
    "Goychay", "Goygol", "Hajigabul", "Imishli", "Ismailli",
    "Jabrayil", "Jalilabad", "Kalbajar", "Lachin", "Lerik",
    "Masally", "Mingachevir", "Nakhchivan", "Neftchala", "Oguz",
    "Qax", "Qazakh", "Quba", "Qubadli", "Qusar",
    "Saatly", "Sabirabad", "Salyan", "Shamakhi", "Shamkir",
    "Shirvan", "Shusha", "Siazan", "Sumgayit", "Tartar",
    "Tovuz", "Ujar", "Khachmaz", "Khankendi", "Khizi",
    "Baku", "Ganja", "Lankaran", "Shaki", "Zaqatala", "Zardab",
]
AZERBAIJAN_MUNICIPALITIES: Dict[str, List[str]] = {
    "Baku": ["Baku City", "Sabunchu", "Surakhani", "Binagadi", "Narimanov"],
    "Ganja": ["Ganja City", "Khanlar"],
    "Sumgayit": ["Sumgayit City"],
    "Lankaran": ["Lankaran City", "Astara City"],
    "Shaki": ["Shaki City", "Oguz"],
    "Nakhchivan": ["Nakhchivan City", "Ordubad", "Julfa"],
}

# ── Bahamas ───────────────────────────────────────────────────────────────────
BAHAMAS_DISTRICTS: List[str] = [
    "Acklins", "Berry Islands", "Bimini", "Black Point", "Cat Island",
    "Central Abaco", "Central Andros", "Central Eleuthera",
    "City of Freeport", "Crooked Island and Long Cay", "East Grand Bahama",
    "Exuma", "Grand Cay", "Harbour Island", "Hope Town", "Inagua",
    "Long Island", "Mangrove Cay", "Mayaguana", "Moore's Island",
    "New Providence", "North Abaco", "North Andros", "North Eleuthera",
    "Ragged Island", "Rum Cay", "San Salvador", "South Abaco",
    "South Andros", "South Eleuthera", "Spanish Wells", "West Grand Bahama",
]
BAHAMAS_SETTLEMENTS: Dict[str, List[str]] = {
    "New Providence": ["Nassau", "Carmichael", "Nassau Village"],
    "City of Freeport": ["Freeport", "Eight Mile Rock", "West End"],
    "Exuma": ["George Town", "Moss Town"],
    "Long Island": ["Clarence Town", "Deadman's Cay"],
}

# ── Bahrain ───────────────────────────────────────────────────────────────────
BAHRAIN_GOVERNORATES: List[str] = [
    "Capital", "Muharraq", "Northern", "Southern",
]
BAHRAIN_MUNICIPALITIES: Dict[str, List[str]] = {
    "Capital": ["Manama", "Juffair", "Adliya", "Seef", "Gudaibiya"],
    "Muharraq": ["Muharraq City", "Hidd", "Arad", "Busaiteen"],
    "Northern": ["Manamah", "Sitra", "Budaiya", "Barbar", "Hamad Town"],
    "Southern": ["Riffa", "Isa Town", "Zallaq", "Awali"],
}

# ── Bangladesh ────────────────────────────────────────────────────────────────
BANGLADESH_DIVISIONS: List[str] = [
    "Barisal", "Chittagong", "Dhaka", "Khulna",
    "Mymensingh", "Rajshahi", "Rangpur", "Sylhet",
]
BANGLADESH_DISTRICTS: Dict[str, List[str]] = {
    "Dhaka": ["Dhaka", "Gazipur", "Narayanganj", "Manikganj", "Munshiganj", "Narsingdi"],
    "Chittagong": ["Chittagong", "Cox's Bazar", "Comilla", "Feni", "Noakhali", "Chandpur"],
    "Rajshahi": ["Rajshahi", "Bogura", "Pabna", "Naogaon", "Natore", "Sirajganj", "Chapainawabganj"],
    "Khulna": ["Khulna", "Jessore", "Satkhira", "Bagerhat", "Chuadanga", "Kushtia", "Magura"],
    "Sylhet": ["Sylhet", "Moulvibazar", "Habiganj", "Sunamganj"],
    "Barisal": ["Barisal", "Bhola", "Patuakhali", "Pirojpur", "Barguna", "Jhalokati"],
    "Mymensingh": ["Mymensingh", "Netrokona", "Sherpur", "Jamalpur"],
    "Rangpur": ["Rangpur", "Dinajpur", "Nilphamari", "Gaibandha", "Kurigram", "Lalmonirhat", "Thakurgaon", "Panchagarh"],
}

# ── Barbados ──────────────────────────────────────────────────────────────────
BARBADOS_PARISHES: List[str] = [
    "Christ Church", "Saint Andrew", "Saint George", "Saint James",
    "Saint John", "Saint Joseph", "Saint Lucy", "Saint Michael",
    "Saint Peter", "Saint Philip", "Saint Thomas",
]
BARBADOS_DISTRICTS: Dict[str, List[str]] = {
    "Saint Michael": ["Bridgetown", "Belleville", "Fontabelle"],
    "Christ Church": ["Oistins", "Worthing", "Hastings", "Maxwell"],
    "Saint James": ["Holetown", "Speightstown"],
    "Saint Philip": ["Six Cross Roads", "Crane"],
    "Saint Peter": ["Speightstown", "Mullins"],
}

# ── Belarus ───────────────────────────────────────────────────────────────────
BELARUS_REGIONS: List[str] = [
    "Brest Region", "Vitebsk Region", "Gomel Region", "Grodno Region",
    "Minsk Region", "Mogilev Region", "Minsk City",
]
BELARUS_DISTRICTS: Dict[str, List[str]] = {
    "Minsk City": ["Minsk City"],
    "Minsk Region": ["Barysaw", "Zhodzina", "Salihorsk", "Maladzyechna", "Vileika"],
    "Brest Region": ["Brest", "Baranavichy", "Pinsk", "Luninets"],
    "Grodno Region": ["Grodno", "Lida", "Slonim", "Novogrudok"],
    "Vitebsk Region": ["Vitebsk", "Orsha", "Polotsk", "Novopolotsk"],
    "Mogilev Region": ["Mogilev", "Bobruisk", "Byhau"],
    "Gomel Region": ["Gomel", "Mazyr", "Zhlobin", "Svetlahorsk"],
}

# ── Belize ────────────────────────────────────────────────────────────────────
BELIZE_DISTRICTS: List[str] = [
    "Belize", "Cayo", "Corozal", "Orange Walk", "Stann Creek", "Toledo",
]
BELIZE_MUNICIPALITIES: Dict[str, List[str]] = {
    "Belize": ["Belize City", "Ladyville", "Hattieville"],
    "Cayo": ["Belmopan", "San Ignacio", "Santa Elena", "Benque Viejo"],
    "Corozal": ["Corozal Town", "Consejo", "Sarteneja"],
    "Orange Walk": ["Orange Walk Town", "Shipyard", "San Estevan"],
    "Stann Creek": ["Dangriga", "Placencia", "Hopkins"],
    "Toledo": ["Punta Gorda", "San Antonio", "Barranco"],
}

# ── Bhutan ────────────────────────────────────────────────────────────────────
BHUTAN_DZONGKHAGS: List[str] = [
    "Bumthang", "Chukha", "Dagana", "Gasa", "Haa",
    "Lhuentse", "Mongar", "Paro", "Pemagatshel", "Punakha",
    "Samdrup Jongkhar", "Samtse", "Sarpang", "Thimphu",
    "Trashigang", "Trashiyangtse", "Trongsa", "Tsirang",
    "Wangdue Phodrang", "Zhemgang",
]
BHUTAN_GEWOGS: Dict[str, List[str]] = {
    "Thimphu": ["Chang", "Dagala", "Genyekha", "Kawang", "Lingzhi", "Mewang", "Naro", "Toedchen"],
    "Paro": ["Doga", "Doteng", "Lamgong", "Lungnyi", "Naja", "Tsento", "Wangchang"],
    "Punakha": ["Barp", "Bayi", "Chhubu", "Guma", "Kamichu", "Talo", "Toewang"],
    "Chukha": ["Bongo", "Chapcha", "Darla", "Dungna", "Getana", "Logchina", "Phuntsholing"],
    "Bumthang": ["Chhoekhor", "Chumey", "Tang", "Ura"],
}

# ── Bolivia ───────────────────────────────────────────────────────────────────
BOLIVIA_DEPARTMENTS: List[str] = [
    "Beni", "Chuquisaca", "Cochabamba", "La Paz", "Oruro",
    "Pando", "Potosí", "Santa Cruz", "Tarija",
]
BOLIVIA_MUNICIPALITIES: Dict[str, List[str]] = {
    "La Paz": ["La Paz City", "El Alto", "Viacha", "Achacachi", "Copacabana"],
    "Santa Cruz": ["Santa Cruz de la Sierra", "Montero", "Warnes", "Cotoca", "Porongo"],
    "Cochabamba": ["Cochabamba City", "Sacaba", "Quillacollo", "Tiquipaya", "Colcapirhua"],
    "Potosí": ["Potosí City", "Villazón", "Uyuni", "Tupiza"],
    "Oruro": ["Oruro City", "Huanuni", "Challapata"],
    "Chuquisaca": ["Sucre", "Camargo", "Monteagudo"],
    "Tarija": ["Tarija City", "Yacuiba", "Villam"],
    "Beni": ["Trinidad", "Riberalta", "Guayaramerín"],
    "Pando": ["Cobija", "Porvenir"],
}

# ── Bosnia and Herzegovina ────────────────────────────────────────────────────
BOSNIA_ENTITIES: List[str] = [
    "Federation of Bosnia and Herzegovina", "Republika Srpska",
    "Brčko District",
]
BOSNIA_CANTONS: Dict[str, List[str]] = {
    "Federation of Bosnia and Herzegovina": [
        "Una-Sana Canton", "Posavina Canton", "Tuzla Canton", "Zenica-Doboj Canton",
        "Bosnian Podrinje Canton", "Central Bosnia Canton", "Herzegovina-Neretva Canton",
        "West Herzegovina Canton", "Sarajevo Canton", "Canton 10",
    ],
    "Republika Srpska": [
        "Banja Luka", "Bijeljina", "Doboj", "Trebinje", "Zvornik",
    ],
    "Brčko District": ["Brčko"],
}

# ── Brazil ────────────────────────────────────────────────────────────────────
BRAZIL_STATES: List[str] = [
    "Acre", "Alagoas", "Amapá", "Amazonas", "Bahia",
    "Ceará", "Distrito Federal", "Espírito Santo", "Goiás",
    "Maranhão", "Mato Grosso", "Mato Grosso do Sul", "Minas Gerais",
    "Pará", "Paraíba", "Paraná", "Pernambuco", "Piauí",
    "Rio de Janeiro", "Rio Grande do Norte", "Rio Grande do Sul",
    "Rondônia", "Roraima", "Santa Catarina", "São Paulo",
    "Sergipe", "Tocantins",
]
BRAZIL_MUNICIPALITIES: Dict[str, List[str]] = {
    "São Paulo": ["São Paulo City", "Guarulhos", "Campinas", "Santos", "São Bernardo do Campo"],
    "Rio de Janeiro": ["Rio de Janeiro City", "Niterói", "Nova Iguaçu", "Duque de Caxias"],
    "Minas Gerais": ["Belo Horizonte", "Uberlândia", "Contagem", "Juiz de Fora"],
    "Bahia": ["Salvador", "Feira de Santana", "Vitória da Conquista"],
    "Paraná": ["Curitiba", "Londrina", "Maringá", "Ponta Grossa"],
    "Rio Grande do Sul": ["Porto Alegre", "Caxias do Sul", "Pelotas", "Canoas"],
    "Pernambuco": ["Recife", "Olinda", "Caruaru", "Petrolina"],
    "Ceará": ["Fortaleza", "Caucaia", "Juazeiro do Norte", "Maracanaú"],
    "Goiás": ["Goiânia", "Aparecida de Goiânia", "Anápolis"],
    "Amazonas": ["Manaus", "Parintins", "Itacoatiara"],
}

# ── Brunei ────────────────────────────────────────────────────────────────────
BRUNEI_DISTRICTS: List[str] = [
    "Belait", "Brunei-Muara", "Temburong", "Tutong",
]
BRUNEI_MUKIMS: Dict[str, List[str]] = {
    "Brunei-Muara": ["Bandar Seri Begawan", "Berakas A", "Berakas B", "Kota Batu", "Gadong"],
    "Belait": ["Kuala Belait", "Seria", "Labi", "Sukang"],
    "Tutong": ["Tutong Town", "Telisai", "Lamit"],
    "Temburong": ["Bangar", "Batu Apoi", "Amo"],
}

# ── Bulgaria ──────────────────────────────────────────────────────────────────
BULGARIA_PROVINCES: List[str] = [
    "Blagoevgrad", "Burgas", "Dobrich", "Gabrovo", "Haskovo",
    "Kardzhali", "Kyustendil", "Lovech", "Montana", "Pazardzhik",
    "Pernik", "Pleven", "Plovdiv", "Razgrad", "Ruse", "Shumen",
    "Silistra", "Sliven", "Smolyan", "Sofia City", "Sofia Province",
    "Stara Zagora", "Targovishte", "Varna", "Veliko Tarnovo",
    "Vidin", "Vratsa", "Yambol",
]
BULGARIA_MUNICIPALITIES: Dict[str, List[str]] = {
    "Sofia City": ["Sofia", "Bankya", "Novi Iskar", "Pancharevo"],
    "Plovdiv": ["Plovdiv City", "Asenovgrad", "Karlovo", "Rakovsku"],
    "Varna": ["Varna City", "Devnya", "Aksakovo", "Beloslav"],
    "Burgas": ["Burgas City", "Sozopol", "Nessebar", "Pomorie"],
    "Ruse": ["Ruse City", "Byala", "Vetovo"],
    "Stara Zagora": ["Stara Zagora City", "Kazanlak", "Chirpan"],
}

# ── Cambodia ──────────────────────────────────────────────────────────────────
CAMBODIA_PROVINCES: List[str] = [
    "Banteay Meanchey", "Battambang", "Kampong Cham", "Kampong Chhnang",
    "Kampong Speu", "Kampong Thom", "Kampot", "Kandal", "Koh Kong",
    "Kep", "Kratie", "Mondulkiri", "Oddar Meanchey", "Pailin",
    "Phnom Penh", "Preah Sihanouk", "Preah Vihear", "Prey Veng",
    "Pursat", "Ratanakiri", "Siem Reap", "Stung Treng", "Svay Rieng",
    "Takeo", "Tbong Khmum",
]
CAMBODIA_DISTRICTS: Dict[str, List[str]] = {
    "Phnom Penh": ["Chamkarmon", "Doun Penh", "Prampir Meakkakra", "Tuol Kouk", "Dangkao"],
    "Siem Reap": ["Siem Reap District", "Angkor Chum", "Puok", "Prasat Bakong"],
    "Battambang": ["Battambang District", "Banan", "Sangkae", "Thma Koul"],
    "Kampong Cham": ["Kampong Cham District", "Batheay", "Chamkar Leu"],
    "Preah Sihanouk": ["Preah Sihanouk District", "Kampong Seila"],
}

# ── Chile ─────────────────────────────────────────────────────────────────────
CHILE_REGIONS: List[str] = [
    "Arica and Parinacota", "Tarapacá", "Antofagasta", "Atacama",
    "Coquimbo", "Valparaíso", "Metropolitan Region of Santiago",
    "O'Higgins", "Maule", "Ñuble", "Biobío", "La Araucanía",
    "Los Ríos", "Los Lagos", "Aysén", "Magallanes",
]
CHILE_COMMUNES: Dict[str, List[str]] = {
    "Metropolitan Region of Santiago": ["Santiago", "Providencia", "Las Condes", "Maipú", "La Florida"],
    "Valparaíso": ["Valparaíso City", "Viña del Mar", "Quilpué", "Villa Alemana"],
    "Biobío": ["Concepción", "Talcahuano", "Chillán", "Los Ángeles"],
    "La Araucanía": ["Temuco", "Padre Las Casas", "Angol", "Victoria"],
    "Los Lagos": ["Puerto Montt", "Osorno", "Castro", "Ancud"],
    "Antofagasta": ["Antofagasta City", "Calama", "Tocopilla"],
    "Coquimbo": ["La Serena", "Coquimbo City", "Ovalle", "Illapel"],
}

# ── China ─────────────────────────────────────────────────────────────────────
CHINA_PROVINCES: List[str] = [
    "Anhui", "Beijing", "Chongqing", "Fujian", "Gansu",
    "Guangdong", "Guangxi", "Guizhou", "Hainan", "Hebei",
    "Heilongjiang", "Henan", "Hong Kong", "Hubei", "Hunan",
    "Inner Mongolia", "Jiangsu", "Jiangxi", "Jilin", "Liaoning",
    "Macau", "Ningxia", "Qinghai", "Shaanxi", "Shandong",
    "Shanghai", "Shanxi", "Sichuan", "Tianjin", "Tibet",
    "Xinjiang", "Yunnan", "Zhejiang",
]
CHINA_PREFECTURES: Dict[str, List[str]] = {
    "Guangdong": ["Guangzhou", "Shenzhen", "Foshan", "Dongguan", "Zhuhai", "Shantou"],
    "Jiangsu": ["Nanjing", "Suzhou", "Wuxi", "Nantong", "Changzhou", "Xuzhou"],
    "Shandong": ["Jinan", "Qingdao", "Yantai", "Weifang", "Linyi", "Zibo"],
    "Zhejiang": ["Hangzhou", "Ningbo", "Wenzhou", "Jinhua", "Shaoxing", "Taizhou"],
    "Sichuan": ["Chengdu", "Mianyang", "Deyang", "Leshan", "Nanchong"],
    "Henan": ["Zhengzhou", "Luoyang", "Kaifeng", "Nanyang", "Anyang"],
    "Hubei": ["Wuhan", "Yichang", "Xiangyang", "Jingzhou"],
    "Hunan": ["Changsha", "Zhuzhou", "Xiangtan", "Hengyang"],
    "Beijing": ["Chaoyang", "Haidian", "Fengtai", "Dongcheng", "Xicheng"],
    "Shanghai": ["Pudong", "Jing'an", "Xuhui", "Huangpu", "Yangpu"],
}

# ── Colombia ──────────────────────────────────────────────────────────────────
COLOMBIA_DEPARTMENTS: List[str] = [
    "Amazonas", "Antioquia", "Arauca", "Atlántico", "Bolívar",
    "Boyacá", "Caldas", "Caquetá", "Casanare", "Cauca",
    "Cesar", "Chocó", "Córdoba", "Cundinamarca", "Guainía",
    "Guaviare", "Huila", "La Guajira", "Magdalena", "Meta",
    "Nariño", "Norte de Santander", "Putumayo", "Quindío",
    "Risaralda", "San Andrés y Providencia", "Santander", "Sucre",
    "Tolima", "Valle del Cauca", "Vaupés", "Vichada",
    "Bogotá D.C.",
]
COLOMBIA_MUNICIPALITIES: Dict[str, List[str]] = {
    "Bogotá D.C.": ["Bogotá City"],
    "Antioquia": ["Medellín", "Bello", "Envigado", "Itagüí", "Bucaramanga"],
    "Valle del Cauca": ["Cali", "Buenaventura", "Palmira", "Buga", "Tulúa"],
    "Cundinamarca": ["Soacha", "Fusagasugá", "Facatativá", "Zipaquirá"],
    "Atlántico": ["Barranquilla", "Soledad", "Malambo", "Sabanalarga"],
    "Bolívar": ["Cartagena", "Magangué", "El Carmen de Bolívar"],
    "Santander": ["Bucaramanga", "Floridablanca", "Girón", "Piedecuesta"],
}

# ── Costa Rica ────────────────────────────────────────────────────────────────
COSTA_RICA_PROVINCES: List[str] = [
    "Alajuela", "Cartago", "Guanacaste", "Heredia",
    "Limón", "Puntarenas", "San José",
]
COSTA_RICA_CANTONS: Dict[str, List[str]] = {
    "San José": ["San José City", "Escazú", "Desamparados", "Aserrí", "Moravia"],
    "Alajuela": ["Alajuela City", "San Ramón", "Grecia", "San Carlos", "Palmares"],
    "Cartago": ["Cartago City", "Paraíso", "La Unión", "Turrialba"],
    "Heredia": ["Heredia City", "Barva", "Santo Domingo", "Santa Bárbara"],
    "Guanacaste": ["Liberia", "Nicoya", "Santa Cruz", "Bagaces"],
    "Puntarenas": ["Puntarenas City", "Quepos", "Osa", "Golfito"],
    "Limón": ["Limón City", "Pococí", "Siquirres", "Talamanca"],
}

# ── Croatia ───────────────────────────────────────────────────────────────────
CROATIA_COUNTIES: List[str] = [
    "Bjelovar-Bilogora", "Brod-Posavina", "Dubrovnik-Neretva",
    "Istria", "Karlovac", "Koprivnica-Križevci", "Krapina-Zagorje",
    "Lika-Senj", "Međimurje", "Osijek-Baranja", "Požega-Slavonia",
    "Primorje-Gorski Kotar", "Šibenik-Knin", "Sisak-Moslavina",
    "Split-Dalmatia", "Varaždin", "Virovitica-Podravina",
    "Vukovar-Srijem", "Zadar", "Zagreb County", "Zagreb City",
]
CROATIA_MUNICIPALITIES: Dict[str, List[str]] = {
    "Zagreb City": ["Zagreb City"],
    "Split-Dalmatia": ["Split", "Kaštela", "Solin", "Trogir", "Makarska"],
    "Primorje-Gorski Kotar": ["Rijeka", "Opatija", "Crikvenica", "Krk"],
    "Osijek-Baranja": ["Osijek", "Đakovo", "Vinkovci"],
    "Istria": ["Pula", "Poreč", "Rovinj", "Umag"],
    "Zadar": ["Zadar City", "Biograd na Moru"],
    "Dubrovnik-Neretva": ["Dubrovnik", "Metković", "Korčula"],
}

# ── Cuba ──────────────────────────────────────────────────────────────────────
CUBA_PROVINCES: List[str] = [
    "Artemisa", "Camagüey", "Ciego de Ávila", "Cienfuegos", "Granma",
    "Guantánamo", "Havana", "Holguín", "Isla de la Juventud", "Las Tunas",
    "Matanzas", "Mayabeque", "Pinar del Río", "Sancti Spíritus",
    "Santiago de Cuba", "Villa Clara",
]
CUBA_MUNICIPALITIES: Dict[str, List[str]] = {
    "Havana": ["Havana City", "Boyeros", "Playa", "Plaza de la Revolución", "Centro Habana"],
    "Santiago de Cuba": ["Santiago City", "Palma Soriano", "Contramaestre"],
    "Holguín": ["Holguín City", "Moa", "Banes", "Gibara"],
    "Camagüey": ["Camagüey City", "Florida", "Nuevitas", "Guáimaro"],
    "Villa Clara": ["Santa Clara", "Cienfuegos City", "Sagua la Grande"],
}

# ── Cyprus ────────────────────────────────────────────────────────────────────
CYPRUS_DISTRICTS: List[str] = [
    "Famagusta", "Kyrenia", "Larnaca", "Limassol", "Nicosia", "Paphos",
]
CYPRUS_MUNICIPALITIES: Dict[str, List[str]] = {
    "Nicosia": ["Nicosia City", "Strovolos", "Lakatamia", "Aglandjia"],
    "Limassol": ["Limassol City", "Germasogeia", "Mesa Geitonia"],
    "Larnaca": ["Larnaca City", "Aradippou", "Livadia"],
    "Paphos": ["Paphos City", "Peyia", "Chlorakas"],
    "Famagusta": ["Paralimni", "Derynia", "Sotira"],
    "Kyrenia": ["Kyrenia City"],
}

# ── Czech Republic ────────────────────────────────────────────────────────────
CZECH_REPUBLIC_REGIONS: List[str] = [
    "Central Bohemian Region", "South Bohemian Region", "Plzeň Region",
    "Karlovy Vary Region", "Ústí nad Labem Region", "Liberec Region",
    "Hradec Králové Region", "Pardubice Region", "Olomouc Region",
    "Moravian-Silesian Region", "South Moravian Region", "Zlín Region",
    "Vysočina Region", "Prague",
]
CZECH_REPUBLIC_DISTRICTS: Dict[str, List[str]] = {
    "Prague": ["Prague 1", "Prague 2", "Prague 3", "Prague 4", "Prague 5", "Prague 6"],
    "South Moravian Region": ["Brno", "Znojmo", "Břeclav", "Hodonín", "Vyškov"],
    "Moravian-Silesian Region": ["Ostrava", "Opava", "Frýdek-Místek", "Karviná"],
    "Plzeň Region": ["Plzeň", "Klatovy", "Domažlice", "Tachov"],
    "Central Bohemian Region": ["Mladá Boleslav", "Kladno", "Příbram", "Nymburk"],
    "Ústí nad Labem Region": ["Ústí nad Labem", "Most", "Teplice", "Chomutov"],
}

# ── Denmark ───────────────────────────────────────────────────────────────────
DENMARK_REGIONS: List[str] = [
    "Capital Region of Denmark", "Central Denmark Region",
    "North Denmark Region", "Region of Southern Denmark", "Region Zealand",
]
DENMARK_MUNICIPALITIES: Dict[str, List[str]] = {
    "Capital Region of Denmark": ["Copenhagen", "Frederiksberg", "Gentofte", "Gladsaxe", "Ballerup"],
    "Central Denmark Region": ["Aarhus", "Silkeborg", "Randers", "Horsens", "Viborg"],
    "Region of Southern Denmark": ["Odense", "Esbjerg", "Vejle", "Kolding", "Sønderborg"],
    "North Denmark Region": ["Aalborg", "Hjørring", "Frederikshavn", "Thisted"],
    "Region Zealand": ["Roskilde", "Slagelse", "Køge", "Næstved", "Holbæk"],
}

# ── Dominica ──────────────────────────────────────────────────────────────────
DOMINICA_PARISHES: List[str] = [
    "Saint Andrew", "Saint David", "Saint George", "Saint John",
    "Saint Joseph", "Saint Luke", "Saint Mark", "Saint Patrick",
    "Saint Paul", "Saint Peter",
]
DOMINICA_VILLAGES: Dict[str, List[str]] = {
    "Saint George": ["Roseau", "Canefield"],
    "Saint Andrew": ["Marigot", "Wesley", "Woodford Hill"],
    "Saint John": ["Portsmouth", "Glanvillia"],
    "Saint Peter": ["Colihaut", "Dublanc"],
    "Saint Patrick": ["Berekua", "Grand Bay"],
}

# ── Dominican Republic ────────────────────────────────────────────────────────
DOMINICAN_REPUBLIC_PROVINCES: List[str] = [
    "Azua", "Bahoruco", "Barahona", "Dajabón", "Distrito Nacional",
    "Duarte", "El Seibo", "Elías Piña", "Espaillat", "Hato Mayor",
    "Hermanas Mirabal", "Independencia", "La Altagracia", "La Romana",
    "La Vega", "María Trinidad Sánchez", "Monseñor Nouel", "Monte Cristi",
    "Monte Plata", "Pedernales", "Peravia", "Puerto Plata", "Samaná",
    "San Cristóbal", "San José de Ocoa", "San Juan", "San Pedro de Macorís",
    "Sánchez Ramírez", "Santiago", "Santiago Rodríguez", "Santo Domingo",
    "Valverde",
]
DOMINICAN_REPUBLIC_MUNICIPALITIES: Dict[str, List[str]] = {
    "Distrito Nacional": ["Santo Domingo City"],
    "Santo Domingo": ["Santo Domingo Este", "Santo Domingo Norte", "Santo Domingo Oeste", "Boca Chica"],
    "Santiago": ["Santiago de los Caballeros", "Villa Bisono", "Moca"],
    "La Altagracia": ["Higüey", "San Rafael del Yuma"],
    "La Romana": ["La Romana City", "San Pedro de Macorís City"],
}

# ── Ecuador ───────────────────────────────────────────────────────────────────
ECUADOR_PROVINCES: List[str] = [
    "Azuay", "Bolívar", "Cañar", "Carchi", "Chimborazo",
    "Cotopaxi", "El Oro", "Esmeraldas", "Galápagos", "Guayas",
    "Imbabura", "Loja", "Los Ríos", "Manabí", "Morona Santiago",
    "Napo", "Orellana", "Pastaza", "Pichincha", "Santa Elena",
    "Santo Domingo de los Tsáchilas", "Sucumbíos", "Tungurahua",
    "Zamora Chinchipe",
]
ECUADOR_CANTONS: Dict[str, List[str]] = {
    "Pichincha": ["Quito", "Cayambe", "Mejía", "Pedro Moncayo", "Rumiñahui"],
    "Guayas": ["Guayaquil", "Samborondón", "Durán", "Daule", "Milagro"],
    "Azuay": ["Cuenca", "Gualaceo", "Paute", "Sigsig"],
    "Manabí": ["Portoviejo", "Manta", "Chone", "El Carmen", "Jipijapa"],
    "El Oro": ["Machala", "Santa Rosa", "Pasaje", "Huaquillas"],
    "Tungurahua": ["Ambato", "Baños", "Pelileo", "Tisaleo"],
}

# ── El Salvador ───────────────────────────────────────────────────────────────
EL_SALVADOR_DEPARTMENTS: List[str] = [
    "Ahuachapán", "Cabañas", "Chalatenango", "Cuscatlán", "La Libertad",
    "La Paz", "La Unión", "Morazán", "San Miguel", "San Salvador",
    "San Vicente", "Santa Ana", "Sonsonate", "Usulután",
]
EL_SALVADOR_MUNICIPALITIES: Dict[str, List[str]] = {
    "San Salvador": ["San Salvador City", "Mejicanos", "Soyapango", "Apopa", "Ayutuxtepeque"],
    "Santa Ana": ["Santa Ana City", "Chalchuapa", "Metapán"],
    "La Libertad": ["Santa Tecla", "Antiguo Cuscatlán", "Quezaltepeque"],
    "Sonsonate": ["Sonsonate City", "Acajutla", "Nahuizalco"],
    "San Miguel": ["San Miguel City", "Moncagua", "Ciudad Barrios"],
}

# ── Estonia ───────────────────────────────────────────────────────────────────
ESTONIA_COUNTIES: List[str] = [
    "Harju", "Hiiu", "Ida-Viru", "Järva", "Jõgeva",
    "Lääne", "Lääne-Viru", "Põlva", "Pärnu", "Rapla",
    "Saare", "Tartu", "Valga", "Viljandi", "Võru",
]
ESTONIA_MUNICIPALITIES: Dict[str, List[str]] = {
    "Harju": ["Tallinn", "Maardu", "Saue", "Keila", "Paldiski"],
    "Tartu": ["Tartu City", "Elva", "Võru City"],
    "Ida-Viru": ["Narva", "Kohtla-Järve", "Sillamäe", "Jõhvi"],
    "Pärnu": ["Pärnu City", "Paide"],
    "Lääne-Viru": ["Rakvere", "Tapa"],
}

# ── Fiji ──────────────────────────────────────────────────────────────────────
FIJI_DIVISIONS: List[str] = [
    "Central", "Eastern", "Northern", "Western",
]
FIJI_PROVINCES: Dict[str, List[str]] = {
    "Central": ["Suva", "Nausori", "Navua", "Korovou", "Levuka"],
    "Western": ["Lautoka", "Nadi", "Ba", "Sigatoka", "Tavua"],
    "Northern": ["Labasa", "Savusavu", "Seaqaqa"],
    "Eastern": ["Levuka Town", "Lomaiviti", "Lau", "Kadavu"],
}

# ── Finland ───────────────────────────────────────────────────────────────────
FINLAND_REGIONS: List[str] = [
    "Åland Islands", "Central Finland", "Central Ostrobothnia",
    "Finland Proper", "Kainuu", "Kymenlaakso", "Lapland",
    "North Karelia", "North Ostrobothnia", "North Savo",
    "Ostrobothnia", "Päijänne Tavastia", "Pirkanmaa",
    "Satakunta", "South Karelia", "South Ostrobothnia",
    "South Savo", "Tavastia Proper", "Uusimaa",
]
FINLAND_MUNICIPALITIES: Dict[str, List[str]] = {
    "Uusimaa": ["Helsinki", "Espoo", "Vantaa", "Tampere", "Porvoo"],
    "Pirkanmaa": ["Tampere", "Nokia", "Ylöjärvi", "Kangasala"],
    "Finland Proper": ["Turku", "Salo", "Naantali", "Raisio"],
    "North Ostrobothnia": ["Oulu", "Raahe", "Ylivieska", "Oulainen"],
    "Lapland": ["Rovaniemi", "Kemi", "Tornio", "Kemijärvi"],
    "Central Finland": ["Jyväskylä", "Jämsä", "Keuruu"],
}

# ── Georgia ───────────────────────────────────────────────────────────────────
GEORGIA_REGIONS: List[str] = [
    "Adjara", "Guria", "Imereti", "Kakheti", "Kvemo Kartli",
    "Mtskheta-Mtianeti", "Racha-Lechkhumi and Kvemo Svaneti",
    "Samegrelo-Zemo Svaneti", "Samtskhe-Javakheti", "Shida Kartli",
    "Tbilisi",
]
GEORGIA_MUNICIPALITIES: Dict[str, List[str]] = {
    "Tbilisi": ["Tbilisi City"],
    "Adjara": ["Batumi", "Kobuleti", "Khelvachauri", "Keda"],
    "Imereti": ["Kutaisi", "Zestaponi", "Samtredia", "Chiatura"],
    "Kakheti": ["Telavi", "Akhmeta", "Gurjaani", "Lagodekhi"],
    "Kvemo Kartli": ["Rustavi", "Gardabani", "Marneuli", "Bolnisi"],
    "Shida Kartli": ["Gori", "Kaspi", "Kareli"],
    "Mtskheta-Mtianeti": ["Mtskheta", "Dusheti", "Tianeti"],
}

# ── Greece ────────────────────────────────────────────────────────────────────
GREECE_REGIONS: List[str] = [
    "Attica", "Central Greece", "Central Macedonia", "Crete",
    "Eastern Macedonia and Thrace", "Epirus", "Ionian Islands",
    "North Aegean", "Peloponnese", "South Aegean", "Thessaly",
    "Western Greece", "Western Macedonia", "Mount Athos",
]
GREECE_MUNICIPALITIES: Dict[str, List[str]] = {
    "Attica": ["Athens", "Piraeus", "Peristeri", "Kallithea", "Nikaia"],
    "Central Macedonia": ["Thessaloniki", "Kalamaria", "Pavlos Melas", "Ampelokipoi"],
    "Crete": ["Heraklion", "Chania", "Rethymno", "Agios Nikolaos"],
    "Thessaly": ["Larissa", "Volos", "Trikala", "Karditsa"],
    "Peloponnese": ["Patras", "Tripoli", "Kalamata", "Corinth"],
    "Epirus": ["Ioannina", "Arta", "Preveza", "Thesprotia"],
}

# ── Grenada ───────────────────────────────────────────────────────────────────
GRENADA_PARISHES: List[str] = [
    "Saint Andrew", "Saint David", "Saint George", "Saint John",
    "Saint Mark", "Saint Patrick", "Carriacou and Petite Martinique",
]
GRENADA_VILLAGES: Dict[str, List[str]] = {
    "Saint George": ["St. George's City", "Grand Anse", "Calliste"],
    "Saint Andrew": ["Grenville", "Birchgrove"],
    "Saint Patrick": ["Sauteurs", "Victoria"],
    "Carriacou and Petite Martinique": ["Hillsborough"],
}

# ── Guatemala ─────────────────────────────────────────────────────────────────
GUATEMALA_DEPARTMENTS: List[str] = [
    "Alta Verapaz", "Baja Verapaz", "Chimaltenango", "Chiquimula",
    "El Progreso", "Escuintla", "Guatemala", "Huehuetenango",
    "Izabal", "Jalapa", "Jutiapa", "Petén", "Quetzaltenango",
    "Quiché", "Retalhuleu", "Sacatepéquez", "San Marcos",
    "Santa Rosa", "Sololá", "Suchitepéquez", "Totonicapán", "Zacapa",
]
GUATEMALA_MUNICIPALITIES: Dict[str, List[str]] = {
    "Guatemala": ["Guatemala City", "Mixco", "Villa Nueva", "San Juan Sacatepéquez"],
    "Quetzaltenango": ["Quetzaltenango City", "Coatepeque", "San Marcos City"],
    "Escuintla": ["Escuintla City", "Puerto San José", "Masagua"],
    "Petén": ["Flores", "San Benito", "La Libertad"],
    "Izabal": ["Puerto Barrios", "Morales", "El Estor"],
}

# ── Guyana ────────────────────────────────────────────────────────────────────
GUYANA_REGIONS: List[str] = [
    "Barima-Waini", "Cuyuni-Mazaruni", "Demerara-Mahaica",
    "East Berbice-Corentyne", "Essequibo Islands-West Demerara",
    "Mahaica-Berbice", "Pomeroon-Supenaam", "Potaro-Siparuni",
    "Upper Demerara-Berbice", "Upper Takutu-Upper Essequibo",
]
GUYANA_MUNICIPALITIES: Dict[str, List[str]] = {
    "Demerara-Mahaica": ["Georgetown", "Agricola", "Timehri"],
    "East Berbice-Corentyne": ["New Amsterdam", "Berbice", "Corriverton"],
    "Essequibo Islands-West Demerara": ["Vreed-en-Hoop", "Parika"],
    "Mahaica-Berbice": ["Rosignol", "Fort Wellington"],
    "Barima-Waini": ["Mabaruma", "Port Kaituma"],
}

# ── Haiti ─────────────────────────────────────────────────────────────────────
HAITI_DEPARTMENTS: List[str] = [
    "Artibonite", "Centre", "Grand'Anse", "Nippes", "Nord",
    "Nord-Est", "Nord-Ouest", "Ouest", "Sud", "Sud-Est",
]
HAITI_ARRONDISSEMENTS: Dict[str, List[str]] = {
    "Ouest": ["Port-au-Prince", "Croix-des-Bouquets", "Léogâne", "Arcahaie"],
    "Nord": ["Cap-Haïtien", "Acul-du-Nord", "Grande-Rivière-du-Nord"],
    "Artibonite": ["Gonaïves", "Saint-Marc", "Dessalines", "Gros-Morne"],
    "Sud": ["Les Cayes", "Aquin", "Camp-Perrin"],
    "Centre": ["Hinche", "Mirebalais", "Lascahobas"],
}

# ── Honduras ──────────────────────────────────────────────────────────────────
HONDURAS_DEPARTMENTS: List[str] = [
    "Atlántida", "Choluteca", "Colón", "Comayagua", "Copán",
    "Cortés", "El Paraíso", "Francisco Morazán", "Gracias a Dios",
    "Intibucá", "Islas de la Bahía", "La Paz", "Lempira",
    "Ocotepeque", "Olancho", "Santa Bárbara", "Valle", "Yoro",
]
HONDURAS_MUNICIPALITIES: Dict[str, List[str]] = {
    "Francisco Morazán": ["Tegucigalpa", "Distrito Central", "Talanga", "Valle de Ángeles"],
    "Cortés": ["San Pedro Sula", "Puerto Cortés", "Choloma", "La Lima"],
    "Atlántida": ["La Ceiba", "Tela", "La Masica"],
    "Comayagua": ["Comayagua City", "Siguatepeque", "Villanueva"],
    "Olancho": ["Juticalpa", "Catacamas", "Salamá"],
}

# ── Hungary ───────────────────────────────────────────────────────────────────
HUNGARY_COUNTIES: List[str] = [
    "Baranya", "Bács-Kiskun", "Békés", "Borsod-Abaúj-Zemplén",
    "Budapest", "Csongrád-Csanád", "Fejér", "Győr-Moson-Sopron",
    "Hajdú-Bihar", "Heves", "Jász-Nagykun-Szolnok", "Komárom-Esztergom",
    "Nógrád", "Pest", "Somogy", "Szabolcs-Szatmár-Bereg",
    "Tolna", "Vas", "Veszprém", "Zala",
]
HUNGARY_CITIES: Dict[str, List[str]] = {
    "Budapest": ["Budapest City"],
    "Pest": ["Érd", "Gödöllő", "Dunakeszi", "Vác"],
    "Borsod-Abaúj-Zemplén": ["Miskolc", "Kazincbarcika", "Ózd", "Tiszaújváros"],
    "Győr-Moson-Sopron": ["Győr", "Sopron", "Mosonmagyaróvár"],
    "Hajdú-Bihar": ["Debrecen", "Nyíregyháza", "Hajdúböszörmény"],
    "Bács-Kiskun": ["Kecskemét", "Baja", "Kiskunfélegyháza"],
    "Csongrád-Csanád": ["Szeged", "Hódmezővásárhely", "Szentes"],
}

# ── Iceland ───  �───────────────────────────────────────────────────────────────
ICELAND_REGIONS: List[str] = [
    "Capital Region", "Southern Peninsula", "West", "Westfjords",
    "Northwest", "Northeast", "East", "South",
]
ICELAND_MUNICIPALITIES: Dict[str, List[str]] = {
    "Capital Region": ["Reykjavík", "Kópavogur", "Hafnarfjörður", "Akranes", "Garðabær"],
    "South": ["Selfoss", "Hvolsvöllur", "Vestmannaeyjar"],
    "West": ["Akranes", "Borgarnes"],
    "Northeast": ["Akureyri", "Húsavík", "Dalvík"],
    "East": ["Egilsstaðir", "Reyðarfjörður", "Neskaupstaður"],
    "Northwest": ["Ísafjörður", "Bolungarvík"],
}

# ── Indonesia ─────────────────────────────────────────────────────────────────
INDONESIA_PROVINCES: List[str] = [
    "Aceh", "Bali", "Bangka Belitung Islands", "Banten", "Bengkulu",
    "Central Java", "Central Kalimantan", "Central Papua", "Central Sulawesi",
    "East Java", "East Kalimantan", "East Nusa Tenggara", "Gorontalo",
    "Highland Papua", "Jambi", "Jakarta", "Lampung", "Maluku",
    "North Kalimantan", "North Maluku", "North Sulawesi", "North Sumatra",
    "Papua", "Riau", "Riau Islands", "Southeast Sulawesi", "South Kalimantan",
    "South Papua", "South Sulawesi", "South Sumatra", "Southwest Papua",
    "West Java", "West Kalimantan", "West Nusa Tenggara", "West Papua",
    "West Sulawesi", "West Sumatra", "Yogyakarta",
]
INDONESIA_REGENCIES: Dict[str, List[str]] = {
    "Jakarta": ["Central Jakarta", "East Jakarta", "North Jakarta", "South Jakarta", "West Jakarta"],
    "West Java": ["Bandung", "Bekasi", "Bogor", "Depok", "Tangerang"],
    "East Java": ["Surabaya", "Malang", "Sidoarjo", "Gresik", "Pasuruan"],
    "Central Java": ["Semarang", "Solo", "Yogyakarta", "Magelang", "Salatiga"],
    "North Sumatra": ["Medan", "Binjai", "Tebing Tinggi", "Pematang Siantar"],
    "South Sulawesi": ["Makassar", "Palopo", "Pare-Pare"],
    "Bali": ["Denpasar", "Badung", "Gianyar", "Tabanan"],
}

# ── Iran ──────────────────────────────────────────────────────────────────────
IRAN_PROVINCES: List[str] = [
    "Alborz", "Ardabil", "Bushehr", "Chaharmahal and Bakhtiari",
    "East Azerbaijan", "Fars", "Gilan", "Golestan", "Hamadan",
    "Hormozgan", "Ilam", "Isfahan", "Kerman", "Kermanshah",
    "Khuzestan", "Kohgiluyeh and Boyer-Ahmad", "Kurdistan",
    "Lorestan", "Markazi", "Mazandaran", "North Khorasan",
    "Qazvin", "Qom", "Razavi Khorasan", "Semnan",
    "Sistan and Baluchestan", "South Khorasan", "Tehran",
    "West Azerbaijan", "Yazd", "Zanjan",
]
IRAN_COUNTIES: Dict[str, List[str]] = {
    "Tehran": ["Tehran City", "Karaj", "Rey", "Shemiranat", "Islamshahr"],
    "Isfahan": ["Isfahan City", "Kashan", "Najafabad", "Khomeyni Shahr"],
    "Razavi Khorasan": ["Mashhad", "Nishapur", "Sabzevar", "Torbat-e Heydarieh"],
    "Fars": ["Shiraz", "Marvdasht", "Kazerun", "Jahrom"],
    "East Azerbaijan": ["Tabriz", "Maragheh", "Mianeh", "Shabestar"],
    "Khuzestan": ["Ahvaz", "Abadan", "Khorramshahr", "Dezful"],
    "Gilan": ["Rasht", "Lahijan", "Anzali", "Roudbar"],
}

# ── Iraq ──────────────────────────────────────────────────────────────────────
IRAQ_GOVERNORATES: List[str] = [
    "Al Anbar", "Al Muthanna", "Al Qādisiyyah", "An Najaf", "Arbil",
    "As Sulaymaniyyah", "Babil", "Baghdad", "Basra", "Dahuk",
    "Dhi Qar", "Diyala", "Karbala", "Kirkuk", "Maysan",
    "Nineveh", "Saladin", "Wasit",
]
IRAQ_DISTRICTS: Dict[str, List[str]] = {
    "Baghdad": ["Baghdad City", "Abu Ghraib", "Al-Madain", "Tarmiyah"],
    "Basra": ["Basra City", "Abu Al-Khasib", "Qurna", "Shatt Al-Arab"],
    "Nineveh": ["Mosul", "Sinjar", "Telafar", "Hamdaniya"],
    "Arbil": ["Erbil City", "Makhmur", "Shaqlawa", "Mergasor"],
    "Karbala": ["Karbala City", "Ain Al-Tamr"],
    "An Najaf": ["Najaf City", "Al Kufa", "Al Manathira"],
}

# ── Ireland ───────────────────────────────────────────────────────────────────
IRELAND_PROVINCES: List[str] = [
    "Connacht", "Leinster", "Munster", "Ulster",
]
IRELAND_COUNTIES: Dict[str, List[str]] = {
    "Leinster": ["Dublin", "Wicklow", "Kildare", "Meath", "Louth", "Wexford", "Carlow", "Kilkenny", "Offaly", "Laois", "Westmeath", "Longford"],
    "Munster": ["Cork", "Kerry", "Limerick", "Tipperary", "Waterford", "Clare"],
    "Connacht": ["Galway", "Mayo", "Roscommon", "Sligo", "Leitrim"],
    "Ulster": ["Donegal", "Cavan", "Monaghan"],
}

# ── Israel ────────────────────────────────────────────────────────────────────
ISRAEL_DISTRICTS: List[str] = [
    "Central", "Haifa", "Jerusalem", "Northern", "Southern", "Tel Aviv",
]
ISRAEL_SUBDISTRICTS: Dict[str, List[str]] = {
    "Tel Aviv": ["Tel Aviv City", "Ramat Gan", "Petah Tikva", "Bnei Brak", "Holon"],
    "Jerusalem": ["Jerusalem City", "Bethlehem", "Jericho"],
    "Central": ["Rishon LeZion", "Rehovot", "Ashdod", "Bat Yam", "Herzliya"],
    "Haifa": ["Haifa City", "Netanya", "Acre"],
    "Northern": ["Safed", "Tiberias", "Nazareth", "Nahariya"],
    "Southern": ["Beer Sheva", "Eilat", "Arad", "Dimona"],
}

# ── Jamaica ───────────────────────────────────────────────────────────────────
JAMAICA_PARISHES: List[str] = [
    "Clarendon", "Hanover", "Kingston", "Manchester", "Portland",
    "Saint Andrew", "Saint Ann", "Saint Catherine", "Saint Elizabeth",
    "Saint James", "Saint Mary", "Saint Thomas", "Trelawny", "Westmoreland",
]
JAMAICA_COMMUNITIES: Dict[str, List[str]] = {
    "Kingston": ["Kingston City", "Half Way Tree"],
    "Saint Andrew": ["Kingston Metro Area", "Portmore"],
    "Saint Catherine": ["Spanish Town", "Portmore", "Old Harbour"],
    "Saint James": ["Montego Bay", "Falmouth"],
    "Clarendon": ["May Pen", "Chapelton"],
}

# ── Japan ─────────────────────────────────────────────────────────────────────
JAPAN_PREFECTURES: List[str] = [
    "Aichi", "Akita", "Aomori", "Chiba", "Ehime",
    "Fukui", "Fukuoka", "Fukushima", "Gifu", "Gunma",
    "Hiroshima", "Hokkaido", "Hyogo", "Ibaraki", "Ishikawa",
    "Iwate", "Kagawa", "Kagoshima", "Kanagawa", "Kochi",
    "Kumamoto", "Kyoto", "Mie", "Miyagi", "Miyazaki",
    "Nagano", "Nagasaki", "Nara", "Niigata", "Oita",
    "Okayama", "Okinawa", "Osaka", "Saga", "Saitama",
    "Shiga", "Shimane", "Shizuoka", "Tochigi", "Tokushima",
    "Tokyo", "Tottori", "Toyama", "Wakayama", "Yamagata",
    "Yamaguchi", "Yamanashi",
]
JAPAN_MUNICIPALITIES: Dict[str, List[str]] = {
    "Tokyo": ["Shinjuku", "Shibuya", "Chiyoda", "Minato", "Sumida", "Setagaya"],
    "Osaka": ["Osaka City", "Sakai", "Higashiosaka", "Hirakata", "Toyonaka"],
    "Kanagawa": ["Yokohama", "Kawasaki", "Sagamihara", "Kamakura", "Fujisawa"],
    "Aichi": ["Nagoya", "Toyohashi", "Okazaki", "Ichinomiya", "Toyota"],
    "Fukuoka": ["Fukuoka City", "Kitakyushu", "Kurume", "Kasuga", "Omuta"],
    "Hokkaido": ["Sapporo", "Asahikawa", "Hakodate", "Kushiro", "Obihiro"],
    "Hyogo": ["Kobe", "Himeji", "Amagasaki", "Nishimomiya", "Akashi"],
    "Kyoto": ["Kyoto City", "Uji", "Kameoka"],
    "Saitama": ["Saitama City", "Kawaguchi", "Kawagoe", "Tokorozawa"],
    "Chiba": ["Chiba City", "Funabashi", "Matsudo", "Ichikawa"],
}

# ── Jordan ────────────────────────────────────────────────────────────────────
JORDAN_GOVERNORATES: List[str] = [
    "Ajloun", "Aqaba", "Balqa", "Irbid", "Jarash",
    "Karak", "Ma'an", "Madaba", "Mafraq", "Amman",
    "Tafilah", "Zarqa",
]
JORDAN_DISTRICTS: Dict[str, List[str]] = {
    "Amman": ["Amman City", "Wadi Seer", "Sahab", "Naur", "Muwaqqar"],
    "Zarqa": ["Zarqa City", "Russeifa", "Azraq"],
    "Irbid": ["Irbid City", "Ramtha", "Bani Kananah", "Koura"],
    "Aqaba": ["Aqaba City"],
    "Balqa": ["Salt", "Madaba City", "Shouneh"],
    "Mafraq": ["Mafraq City", "Badia"],
}

# ── Kazakhstan ────────────────────────────────────────────────────────────────
KAZAKHSTAN_REGIONS: List[str] = [
    "Abai Region", "Akmola Region", "Aktobe Region", "Almaty Region",
    "Almaty City", "Astana City", "Atyrau Region", "Bayqongyr",
    "East Kazakhstan Region", "Jetisu Region", "Karaganda Region",
    "Kostanay Region", "Kyzylorda Region", "Mangystau Region",
    "North Kazakhstan Region", "Pavlodar Region", "Shymkent City",
    "Turkistan Region", "Ulytau Region", "West Kazakhstan Region",
    "Zhetysu Region",
]
KAZAKHSTAN_DISTRICTS: Dict[str, List[str]] = {
    "Almaty City": ["Almaty City"],
    "Astana City": ["Astana City"],
    "Karaganda Region": ["Karaganda", "Temirtau", "Balkhash", "Zhezkazgan"],
    "East Kazakhstan Region": ["Ust-Kamenogorsk", "Semey", "Ridder"],
    "Aktobe Region": ["Aktobe City", "Alga", "Embi"],
    "Kostanay Region": ["Kostanay City", "Rudny", "Lisakovsk"],
    "Pavlodar Region": ["Pavlodar City", "Ekibastuz", "Aksu"],
}

# ── Kiribati ──────────────────────────────────────────────────────────────────
KIRIBATI_ISLAND_GROUPS: List[str] = [
    "Gilbert Islands", "Line Islands", "Phoenix Islands",
]
KIRIBATI_ISLANDS: Dict[str, List[str]] = {
    "Gilbert Islands": ["Tarawa", "Abaiang", "Abemama", "Butaritari", "Maiana", "Marakei", "Nonouti"],
    "Line Islands": ["Christmas Island (Kiritimati)", "Fanning Island", "Washington Island"],
    "Phoenix Islands": ["Canton", "Enderbury", "Birnie"],
}

# ── North Korea ───────────────────────────────────────────────────────────────
NORTH_KOREA_PROVINCES: List[str] = [
    "Chagang", "North Hamgyong", "South Hamgyong", "North Hwanghae",
    "South Hwanghae", "Kangwon", "North Pyongan", "South Pyongan",
    "Pyongyang", "Rason", "Ryanggang",
]
NORTH_KOREA_COUNTIES: Dict[str, List[str]] = {
    "Pyongyang": ["Pyongyang City", "Mangyongdae", "Moranbong", "Taedong"],
    "South Pyongan": ["Pyongsong", "Nampho", "Anju", "Sunchon"],
    "North Hamgyong": ["Chongjin", "Kimchaek", "Hoeryong", "Musan"],
    "South Hamgyong": ["Hamhung", "Hungnam", "Sinpho", "Tanchon"],
    "North Hwanghae": ["Sariwon", "Sinmak", "Phyongsan"],
}

# ── South Korea ───────────────────────────────────────────────────────────────
SOUTH_KOREA_PROVINCES: List[str] = [
    "Busan", "Chungcheongbuk-do", "Chungcheongnam-do", "Daegu", "Daejeon",
    "Gangwon-do", "Gwangju", "Gyeonggi-do", "Gyeongsangbuk-do",
    "Gyeongsangnam-do", "Incheon", "Jeju-do", "Jeollabuk-do",
    "Jeollanam-do", "Sejong", "Seoul", "Ulsan",
]
SOUTH_KOREA_CITIES: Dict[str, List[str]] = {
    "Seoul": ["Gangnam-gu", "Jongno-gu", "Jung-gu", "Mapo-gu", "Yeongdeungpo-gu"],
    "Gyeonggi-do": ["Suwon", "Seongnam", "Goyang", "Yongin", "Bucheon"],
    "Busan": ["Busan City", "Haeundae-gu", "Suyeong-gu", "Dong-gu"],
    "Incheon": ["Incheon City", "Namdong-gu", "Bupyeong-gu"],
    "Daegu": ["Daegu City", "Dalseo-gu", "Suseong-gu"],
    "Daejeon": ["Daejeon City", "Yuseong-gu", "Seo-gu"],
    "Gwangju": ["Gwangju City", "Buk-gu", "Nam-gu"],
}

# ── Kuwait ────────────────────────────────────────────────────────────────────
KUWAIT_GOVERNORATES: List[str] = [
    "Al Ahmadi", "Al Asimah", "Al Farwaniyah", "Al Jahra",
    "Hawalli", "Mubarak Al-Kabeer",
]
KUWAIT_AREAS: Dict[str, List[str]] = {
    "Al Asimah": ["Kuwait City", "Shuwaikh", "Dasman", "Sharq"],
    "Hawalli": ["Salmiya", "Rumaithiya", "Hawalli District", "Bayan"],
    "Al Farwaniyah": ["Farwaniyah", "Jleeb Al-Shuyoukh", "Khaitan", "Omariya"],
    "Al Ahmadi": ["Ahmadi", "Mahboula", "Mangaf", "Fintas"],
    "Al Jahra": ["Jahra City", "Sulaibiya", "Qasr"],
    "Mubarak Al-Kabeer": ["Mubarak Al-Kabeer Area", "Abu Halifa", "Sabah Al-Salem"],
}

# ── Kyrgyzstan ────────────────────────────────────────────────────────────────
KYRGYZSTAN_REGIONS: List[str] = [
    "Batken", "Bishkek City", "Chuy", "Issyk-Kul",
    "Jalal-Abad", "Naryn", "Osh City", "Osh Region", "Talas",
]
KYRGYZSTAN_DISTRICTS: Dict[str, List[str]] = {
    "Bishkek City": ["Bishkek City"],
    "Osh City": ["Osh City"],
    "Chuy": ["Tokmok", "Kant", "Kemin", "Sokuluk"],
    "Jalal-Abad": ["Jalal-Abad City", "Kara-Suu", "Uzgen", "Nooken"],
    "Osh Region": ["Kara-Kuldja", "Aravan", "Kara-Suu"],
    "Issyk-Kul": ["Karakol", "Balykchy", "Cholpon-Ata"],
    "Naryn": ["Naryn City", "Kochkor", "At-Bashy"],
}

# ── Laos ──────────────────────────────────────────────────────────────────────
LAOS_PROVINCES: List[str] = [
    "Attapeu", "Bokeo", "Bolikhamsai", "Champasak", "Houaphan",
    "Khammouane", "Luang Namtha", "Luang Prabang", "Oudomxay",
    "Phongsali", "Sainyabuli", "Salavan", "Savannakhet",
    "Sekong", "Vientiane Prefecture", "Vientiane Province",
    "Xaisomboun", "Xekong", "Xiengkhouang",
]
LAOS_DISTRICTS: Dict[str, List[str]] = {
    "Vientiane Prefecture": ["Chanthabuly", "Sikhottabong", "Xaysetha", "Sisattanak", "Naxaithong"],
    "Champasak": ["Pakse", "Pakxong", "Mounlapamok"],
    "Savannakhet": ["Kaysone Phomvihane", "Outhoumphone"],
    "Luang Prabang": ["Luang Prabang City", "Xiengngeum", "Phonxai"],
    "Khammouane": ["Thakhek", "Nongbok", "Hinboun"],
}

# ── Latvia ────────────────────────────────────────────────────────────────────
LATVIA_MUNICIPALITIES: List[str] = [
    "Adaži Municipality", "Aizkraukle Municipality", "Aizpute Municipality",
    "Alsunga Municipality", "Alūksne Municipality", "Augšdaugava Municipality",
    "Balvi Municipality", "Bauska Municipality", "Cēsis Municipality",
    "Daugavpils City", "Dobele Municipality", "Dundaga Municipality",
    "Engure Municipality", "Gulbene Municipality", "Jelgava City",
    "Jelgava Municipality", "Jēkabpils Municipality", "Jūrmala City",
    "Kandava Municipality", "Kārsava Municipality", "Ķekava Municipality",
    "Krāslava Municipality", "Kuldīga Municipality", "Liepāja City",
    "Limbaži Municipality", "Līvāni Municipality", "Ludza Municipality",
    "Madona Municipality", "Mārupe Municipality", "Nīca Municipality",
    "Ogre Municipality", "Olaine Municipality", "Preiļi Municipality",
    "Priekuļi Municipality", "Rēzekne City", "Rēzekne Municipality",
    "Rīga City", "Ropaži Municipality", "Rucava Municipality",
    "Rugāji Municipality", "Rūjiena Municipality", "Salaspils Municipality",
    "Saldus Municipality", "Saulkrasti Municipality", "Sigulda Municipality",
    "Smiltene Municipality", "Stopiņi Municipality", "Talsi Municipality",
    "Tukums Municipality", "Vaiņode Municipality", "Valka Municipality",
    "Valmiera City", "Varakļāni Municipality", "Ventspils City",
    "Ventspils Municipality", "Viļaka Municipality", "Viļāni Municipality",
    "Zilupe Municipality",
]
LATVIA_ADMINISTRATIVE_UNITS: Dict[str, List[str]] = {
    "Rīga City": ["Riga City Centre", "Ziepniekkalns", "Purvciems", "Imanta"],
    "Liepāja City": ["Liepāja City"],
    "Daugavpils City": ["Daugavpils City"],
    "Jelgava City": ["Jelgava City"],
    "Valmiera City": ["Valmiera City"],
    "Jūrmala City": ["Jūrmala City"],
    "Rēzekne City": ["Rēzekne City"],
    "Cēsis Municipality": ["Cēsis", "Valmiera"],
}

# ── Lebanon ───────────────────────────────────────────────────────────────────
LEBANON_GOVERNORATES: List[str] = [
    "Akkar", "Baalbek-Hermel", "Beirut", "Beqaa", "Mount Lebanon",
    "Nabatieh", "North Lebanon", "South Lebanon",
]
LEBANON_DISTRICTS: Dict[str, List[str]] = {
    "Beirut": ["Beirut City"],
    "Mount Lebanon": ["Baabda", "Metn", "Jbeil", "Kesrouan", "Chouf", "Aley"],
    "North Lebanon": ["Tripoli", "Zgharta", "Bsharri", "Koura", "Batroun", "Miniyeh-Danniyeh"],
    "South Lebanon": ["Sidon", "Tyre", "Jezzine"],
    "Beqaa": ["Zahlé", "West Beqaa", "Rashaya"],
    "Baalbek-Hermel": ["Baalbek", "Hermel"],
    "Nabatieh": ["Nabatieh", "Bint Jbeil", "Hasbaya", "Marjeyoun"],
    "Akkar": ["Halba", "Akkar El Atika"],
}

# ── Liechtenstein ─────────────────────────────────────────────────────────────
LIECHTENSTEIN_COMMUNES: List[str] = [
    "Balzers", "Eschen", "Gamprin", "Mauren", "Planken",
    "Ruggell", "Schaan", "Schellenberg", "Triesen", "Triesenberg",
    "Vaduz",
]
LIECHTENSTEIN_VILLAGES: Dict[str, List[str]] = {
    "Vaduz": ["Vaduz City"],
    "Schaan": ["Schaan Village"],
    "Balzers": ["Balzers Village"],
    "Triesen": ["Triesen Village"],
    "Triesenberg": ["Triesenberg Village"],
}

# ── Lithuania ─────────────────────────────────────────────────────────────────
LITHUANIA_COUNTIES: List[str] = [
    "Alytus County", "Kaunas County", "Klaipėda County",
    "Marijampolė County", "Panevėžys County", "Šiauliai County",
    "Tauragė County", "Telšiai County", "Utena County", "Vilnius County",
]
LITHUANIA_MUNICIPALITIES: Dict[str, List[str]] = {
    "Vilnius County": ["Vilnius City", "Šalčininkai", "Švenčionys", "Trakai"],
    "Kaunas County": ["Kaunas City", "Kaišiadorys", "Kėdainiai", "Jonava"],
    "Klaipėda County": ["Klaipėda City", "Palanga", "Neringa", "Skuodas"],
    "Šiauliai County": ["Šiauliai City", "Radviliškis", "Kelmė", "Joniškis"],
    "Panevėžys County": ["Panevėžys City", "Biržai", "Kupiškis"],
    "Alytus County": ["Alytus City", "Lazdijai", "Varėna"],
}

# ── Luxembourg ────────────────────────────────────────────────────────────────
LUXEMBOURG_CANTONS: List[str] = [
    "Capellen", "Clervaux", "Diekirch", "Echternach", "Esch-sur-Alzette",
    "Grevenmacher", "Luxembourg", "Mersch", "Redange", "Remich",
    "Vianden", "Wiltz",
]
LUXEMBOURG_COMMUNES: Dict[str, List[str]] = {
    "Luxembourg": ["Luxembourg City", "Strassen", "Hesperange", "Sandweiler"],
    "Esch-sur-Alzette": ["Esch-sur-Alzette", "Differdange", "Dudelange", "Sanem"],
    "Capellen": ["Mamer", "Kehlen", "Garnich"],
    "Mersch": ["Mersch", "Fischbach", "Larochette"],
    "Diekirch": ["Diekirch City", "Ettelbruck", "Reisdorf"],
    "Clervaux": ["Clervaux", "Wincrange", "Troisvierges"],
}

# ── Malaysia ──────────────────────────────────────────────────────────────────
MALAYSIA_STATES: List[str] = [
    "Johor", "Kedah", "Kelantan", "Kuala Lumpur", "Labuan",
    "Melaka", "Negeri Sembilan", "Pahang", "Penang", "Perak",
    "Perlis", "Putrajaya", "Sabah", "Sarawak", "Selangor",
    "Terengganu",
]
MALAYSIA_DISTRICTS: Dict[str, List[str]] = {
    "Kuala Lumpur": ["Kuala Lumpur City"],
    "Selangor": ["Shah Alam", "Petaling Jaya", "Subang Jaya", "Klang", "Ampang"],
    "Johor": ["Johor Bahru", "Batu Pahat", "Muar", "Kluang", "Segamat"],
    "Perak": ["Ipoh", "Taiping", "Teluk Intan", "Manjung"],
    "Penang": ["Georgetown", "Butterworth", "Seberang Perai"],
    "Sabah": ["Kota Kinabalu", "Sandakan", "Tawau", "Lahad Datu"],
    "Sarawak": ["Kuching", "Miri", "Sibu", "Bintulu"],
    "Pahang": ["Kuantan", "Temerloh", "Bentong", "Raub"],
}

# ── Maldives ──────────────────────────────────────────────────────────────────
MALDIVES_ATOLLS: List[str] = [
    "Haa Alif Atoll", "Haa Dhaalu Atoll", "Shaviyani Atoll", "Noonu Atoll",
    "Raa Atoll", "Baa Atoll", "Lhaviyani Atoll", "Kaafu Atoll",
    "Alifu Alifu Atoll", "Alifu Dhaalu Atoll", "Vaavu Atoll",
    "Meemu Atoll", "Faafu Atoll", "Dhaalu Atoll", "Thaa Atoll",
    "Laamu Atoll", "Gaafu Alifu Atoll", "Gaafu Dhaalu Atoll",
    "Gnaviyani Atoll", "Seenu Atoll", "Malé City",
]
MALDIVES_ISLANDS: Dict[str, List[str]] = {
    "Malé City": ["Malé", "Hulhumalé", "Villingili"],
    "Kaafu Atoll": ["Hulhulé", "Maafushi", "Guraidhoo"],
    "Seenu Atoll": ["Addu City", "Hithadhoo", "Fuvahmulah"],
    "Alifu Alifu Atoll": ["Rasdhoo", "Ukulhas", "Bodufolhudhoo"],
    "Gaafu Dhaalu Atoll": ["Thinadhoo", "Madaveli"],
}

# ── Malta ─────────────────────────────────────────────────────────────────────
MALTA_REGIONS: List[str] = [
    "Gozo and Comino", "Northern Harbour", "Northern",
    "South Eastern", "Southern Harbour", "Western",
]
MALTA_LOCALITIES: Dict[str, List[str]] = {
    "Northern Harbour": ["Valletta", "Floriana", "Sliema", "St. Julian's", "Gżira", "Msida"],
    "Southern Harbour": ["Birgu", "Cospicua", "Kalkara", "Senglea", "Xgħajra"],
    "Northern": ["Mellieħa", "Mġarr", "Mosta", "Naxxar", "San Ġwann"],
    "Western": ["Attard", "Balzan", "Iklin", "Lija", "Mdina", "Rabat"],
    "South Eastern": ["Birżebbuġa", "Marsaxlokk", "Qrendi", "Żurrieq"],
    "Gozo and Comino": ["Victoria (Rabat)", "Marsalforn", "Xlendi", "Nadur"],
}

# ── Marshall Islands ──────────────────────────────────────────────────────────
MARSHALL_ISLANDS_CHAINS: List[str] = [
    "Ratak Chain", "Ralik Chain",
]
MARSHALL_ISLANDS_ATOLLS: Dict[str, List[str]] = {
    "Ratak Chain": ["Majuro", "Arno", "Aur", "Likiep", "Maloelap", "Mili", "Wotje"],
    "Ralik Chain": ["Kwajalein", "Ailinglaplap", "Ebon", "Jaluit", "Namorik", "Namu", "Rongelap", "Wotho", "Ujae"],
}

# ── Mexico ────────────────────────────────────────────────────────────────────
MEXICO_STATES: List[str] = [
    "Aguascalientes", "Baja California", "Baja California Sur", "Campeche",
    "Chiapas", "Chihuahua", "Coahuila", "Colima", "Durango",
    "Guanajuato", "Guerrero", "Hidalgo", "Jalisco", "Mexico City",
    "Mexico State", "Michoacán", "Morelos", "Nayarit", "Nuevo León",
    "Oaxaca", "Puebla", "Querétaro", "Quintana Roo", "San Luis Potosí",
    "Sinaloa", "Sonora", "Tabasco", "Tamaulipas", "Tlaxcala",
    "Veracruz", "Yucatán", "Zacatecas",
]
MEXICO_MUNICIPALITIES: Dict[str, List[str]] = {
    "Mexico City": ["Benito Juárez", "Cuauhtémoc", "Iztapalapa", "Gustavo A. Madero", "Tlalpan"],
    "Jalisco": ["Guadalajara", "Zapopan", "Tlaquepaque", "Tonalá", "Tlajomulco"],
    "Nuevo León": ["Monterrey", "Guadalupe", "San Nicolás", "Apodaca", "General Escobedo"],
    "Puebla": ["Puebla City", "Tehuacán", "San Martín Texmelucan"],
    "Guanajuato": ["León", "Irapuato", "Celaya", "Guanajuato City", "Salamanca"],
    "Veracruz": ["Veracruz City", "Xalapa", "Coatzacoalcos", "Córdoba"],
    "Oaxaca": ["Oaxaca City", "Salina Cruz", "Juchitán"],
    "Chihuahua": ["Juárez", "Chihuahua City", "Delicias", "Cuauhtémoc"],
}

# ── Micronesia ────────────────────────────────────────────────────────────────
MICRONESIA_STATES: List[str] = [
    "Chuuk", "Kosrae", "Pohnpei", "Yap",
]
MICRONESIA_MUNICIPALITIES: Dict[str, List[str]] = {
    "Pohnpei": ["Palikir", "Kolonia", "Kitti", "Madolenihmw"],
    "Chuuk": ["Weno", "Faichuk", "Ruo"],
    "Yap": ["Colonia", "Tomil-Gagil", "Map"],
    "Kosrae": ["Tofol", "Lelu", "Malem"],
}

# ── Moldova ───────────────────────────────────────────────────────────────────
MOLDOVA_DISTRICTS: List[str] = [
    "Anenii Noi", "Basarabeasca", "Briceni", "Cahul", "Cantemir",
    "Călărași", "Căușeni", "Cimișlia", "Criuleni", "Dondușeni",
    "Drochia", "Dubăsari", "Edineț", "Fălești", "Florești",
    "Glodeni", "Hîncești", "Ialoveni", "Leova", "Nisporeni",
    "Ocnița", "Orhei", "Rezina", "Rîșcani", "Sîngerei",
    "Soroca", "Strășeni", "Șoldănești", "Ștefan Vodă", "Taraclia",
    "Telenești", "Ungheni", "Chișinău Municipality",
    "Bălți Municipality", "Comrat Municipality", "Tiraspol Municipality",
]
MOLDOVA_LOCALITIES: Dict[str, List[str]] = {
    "Chișinău Municipality": ["Chișinău City", "Cricova", "Stăuceni"],
    "Bălți Municipality": ["Bălți City"],
    "Orhei": ["Orhei City", "Rezina City"],
    "Ungheni": ["Ungheni City"],
    "Soroca": ["Soroca City", "Floriești"],
    "Cahul": ["Cahul City", "Leova City"],
}

# ── Monaco ────────────────────────────────────────────────────────────────────
MONACO_WARDS: List[str] = [
    "Fontvieille", "La Condamine", "Larvotto", "Les Moneghetti",
    "Monaco-Ville", "Monte Carlo", "Moneghetti",
]
MONACO_QUARTERS: Dict[str, List[str]] = {
    "Monte Carlo": ["Monte Carlo"],
    "Monaco-Ville": ["Monaco City"],
    "La Condamine": ["La Condamine Quarter"],
    "Larvotto": ["Larvotto Quarter"],
    "Fontvieille": ["Fontvieille Quarter"],
}

# ── Mongolia ──────────────────────────────────────────────────────────────────
MONGOLIA_PROVINCES: List[str] = [
    "Arkhangai", "Bayan-Ölgii", "Bayankhongor", "Bulgan", "Darkhan-Uul",
    "Dornod", "Dornogovi", "Dundgovi", "Govi-Altai", "Govisümber",
    "Khentii", "Khovd", "Khövsgöl", "Orkhon", "Övörkhangai",
    "Selenge", "Sükhbaatar", "Töv", "Ulaanbaatar", "Uvs", "Zavkhan",
]
MONGOLIA_DISTRICTS: Dict[str, List[str]] = {
    "Ulaanbaatar": ["Bayangol", "Bayanzürkh", "Chingeltei", "Songino Khairkhan", "Sükhbaatar"],
    "Darkhan-Uul": ["Darkhan City", "Khongor"],
    "Orkhon": ["Erdenet City"],
    "Selenge": ["Sükhbaatar City", "Zuunbulag"],
    "Töv": ["Zuunmod", "Lün"],
    "Khövsgöl": ["Mörön", "Khatgal"],
}

# ── Montenegro ────────────────────────────────────────────────────────────────
MONTENEGRO_MUNICIPALITIES: List[str] = [
    "Andrijevica", "Bar", "Berane", "Bijelo Polje", "Budva",
    "Cetinje", "Danilovgrad", "Gusinje", "Herceg Novi", "Kolašin",
    "Kotor", "Mojkovac", "Nikšić", "Petnjica", "Plav",
    "Pljevlja", "Plužine", "Podgorica", "Rožaje", "Šavnik",
    "Tivat", "Tuzi", "Ulcinj", "Žabljak",
]
MONTENEGRO_SETTLEMENTS: Dict[str, List[str]] = {
    "Podgorica": ["Podgorica City", "Golubovci", "Tuzi"],
    "Nikšić": ["Nikšić City", "Šavnik"],
    "Bar": ["Bar City", "Ulcinj City"],
    "Budva": ["Budva City", "Petrovac"],
    "Kotor": ["Kotor City", "Tivat City"],
    "Herceg Novi": ["Herceg Novi City"],
}

# ── Myanmar ───────────────────────────────────────────────────────────────────
MYANMAR_STATES_REGIONS: List[str] = [
    "Ayeyarwady Region", "Bago Region", "Chin State", "Kachin State",
    "Kayah State", "Kayin State", "Magway Region", "Mandalay Region",
    "Mon State", "Naypyidaw Union Territory", "Rakhine State",
    "Sagaing Region", "Shan State", "Tanintharyi Region",
    "Yangon Region",
]
MYANMAR_TOWNSHIPS: Dict[str, List[str]] = {
    "Yangon Region": ["Yangon City", "Insein", "Thingangyun", "Dagon", "Hlaing"],
    "Mandalay Region": ["Mandalay City", "Amarapura", "Sagaing", "Kyaukse"],
    "Bago Region": ["Bago City", "Toungoo", "Nyaunglebin"],
    "Magway Region": ["Magway City", "Pakokku", "Yenangyaung"],
    "Sagaing Region": ["Sagaing City", "Monywa", "Shwebo"],
    "Shan State": ["Taunggyi", "Lashio", "Kengtung"],
    "Ayeyarwady Region": ["Pathein", "Hinthada", "Myaungmya"],
    "Naypyidaw Union Territory": ["Naypyidaw City"],
}

# ── Nauru ─────────────────────────────────────────────────────────────────────
NAURU_DISTRICTS: List[str] = [
    "Aiwo", "Anabar", "Anetan", "Anibare", "Baitsi", "Boe",
    "Buada", "Denigomodu", "Ewa", "Ijuw", "Meneng", "Nibok",
    "Uaboe", "Yaren",
]
NAURU_LOCALITIES: Dict[str, List[str]] = {
    "Yaren": ["Yaren District"],
    "Aiwo": ["Aiwo District"],
    "Buada": ["Buada District"],
    "Meneng": ["Meneng District"],
    "Denigomodu": ["Denigomodu District"],
}

# ── Nepal ─────────────────────────────────────────────────────────────────────
NEPAL_PROVINCES: List[str] = [
    "Koshi Province", "Madhesh Province", "Bagmati Province",
    "Gandaki Province", "Lumbini Province", "Karnali Province",
    "Sudurpashchim Province",
]
NEPAL_DISTRICTS: Dict[str, List[str]] = {
    "Bagmati Province": ["Kathmandu", "Lalitpur", "Bhaktapur", "Chitwan", "Makwanpur"],
    "Koshi Province": ["Sunsari", "Morang", "Dhankuta", "Terhathum", "Bhojpur"],
    "Madhesh Province": ["Saptari", "Siraha", "Dhanusha", "Mahottari", "Sarlahi"],
    "Gandaki Province": ["Kaski", "Tanahu", "Syangja", "Lamjung", "Gorkha"],
    "Lumbini Province": ["Rupandehi", "Kapilvastu", "Palpa", "Arghakhanchi"],
    "Karnali Province": ["Surkhet", "Dailekh", "Jumla", "Dolpa"],
    "Sudurpashchim Province": ["Kanchanpur", "Kailali", "Doti", "Bajhang"],
}

# ── New Zealand ───────────────────────────────────────────────────────────────
NEW_ZEALAND_REGIONS: List[str] = [
    "Auckland", "Bay of Plenty", "Canterbury", "Gisborne", "Hawke's Bay",
    "Manawatu-Whanganui", "Marlborough", "Nelson", "Northland",
    "Otago", "Southland", "Taranaki", "Tasman", "Waikato",
    "Wellington", "West Coast",
]
NEW_ZEALAND_DISTRICTS: Dict[str, List[str]] = {
    "Auckland": ["Auckland City", "North Shore City", "Waitakere City", "Manukau City"],
    "Wellington": ["Wellington City", "Lower Hutt", "Upper Hutt", "Porirua"],
    "Canterbury": ["Christchurch City", "Selwyn", "Waimakariri"],
    "Waikato": ["Hamilton City", "Thames-Coromandel", "Waipa"],
    "Bay of Plenty": ["Tauranga City", "Rotorua", "Whakatāne"],
    "Otago": ["Dunedin City", "Queenstown-Lakes", "Central Otago"],
    "Hawke's Bay": ["Napier City", "Hastings"],
    "Manawatu-Whanganui": ["Palmerston North City", "Manawatu"],
}

# ── Nicaragua ─────────────────────────────────────────────────────────────────
NICARAGUA_DEPARTMENTS: List[str] = [
    "Boaco", "Carazo", "Chinandega", "Chontales", "Estelí", "Granada",
    "Jinotega", "León", "Madriz", "Managua", "Masaya", "Matagalpa",
    "Nueva Segovia", "Río San Juan", "Rivas",
    "North Caribbean Coast", "South Caribbean Coast",
]
NICARAGUA_MUNICIPALITIES: Dict[str, List[str]] = {
    "Managua": ["Managua City", "Tipitapa", "Ciudad Sandino", "Mateare"],
    "León": ["León City", "Chichigalpa", "Chinandega City", "El Viejo"],
    "Masaya": ["Masaya City", "Nindirí", "Jinotepe"],
    "Granada": ["Granada City", "Nandaime"],
    "Estelí": ["Estelí City", "Condega", "La Trinidad"],
}

# ── North Macedonia ───────────────────────────────────────────────────────────
NORTH_MACEDONIA_REGIONS: List[str] = [
    "Skopje Region", "Pelagonia Region", "Vardar Region", "Southeast Region",
    "East Region", "Northeast Region", "Southwest Region", "Polog Region",
]
NORTH_MACEDONIA_MUNICIPALITIES: Dict[str, List[str]] = {
    "Skopje Region": ["Skopje City", "Čair", "Gazi Baba", "Kisela Voda", "Karpoš"],
    "Pelagonia Region": ["Bitola", "Herakleia", "Prilepsko"],
    "Polog Region": ["Tetovo", "Gostivar", "Jegunovce"],
    "Southwest Region": ["Ohrid", "Struga", "Resen"],
    "East Region": ["Štip", "Radoviš", "Kočani"],
    "Vardar Region": ["Veles", "Kavadarci", "Negotino"],
}

# ── Norway ────────────────────────────────────────────────────────────────────
NORWAY_COUNTIES: List[str] = [
    "Agder", "Innlandet", "Møre og Romsdal", "Nordland",
    "Oslo", "Rogaland", "Troms og Finnmark", "Trøndelag",
    "Vestfold og Telemark", "Vestland", "Viken",
]
NORWAY_MUNICIPALITIES: Dict[str, List[str]] = {
    "Oslo": ["Oslo City"],
    "Viken": ["Bærum", "Lillestrøm", "Fredrikstad", "Sarpsborg", "Drammen"],
    "Vestland": ["Bergen", "Fjord", "Alver", "Bjørnafjorden"],
    "Rogaland": ["Stavanger", "Sandnes", "Sola", "Klepp"],
    "Trøndelag": ["Trondheim", "Stjørdal", "Steinkjer", "Melhus"],
    "Innlandet": ["Hamar", "Gjøvik", "Lillehammer", "Ringsaker"],
    "Agder": ["Kristiansand", "Arendal", "Grimstad", "Vennesla"],
}

# ── Oman ──────────────────────────────────────────────────────────────────────
OMAN_GOVERNORATES: List[str] = [
    "Ad Dakhiliyah", "Ad Dhahirah", "Al Batinah North", "Al Batinah South",
    "Al Buraymi", "Al Wusta", "Ash Sharqiyah North", "Ash Sharqiyah South",
    "Dhofar", "Musandam", "Muscat",
]
OMAN_DISTRICTS: Dict[str, List[str]] = {
    "Muscat": ["Muscat City", "Muttrah", "Seeb", "Bausher", "Al Amerat"],
    "Dhofar": ["Salalah", "Thumrait", "Mirbat", "Rakhyut"],
    "Al Batinah North": ["Sohar", "Shinas", "Liwa"],
    "Al Batinah South": ["Rustaq", "Al Awabi", "Nakhal"],
    "Ad Dakhiliyah": ["Nizwa", "Bahla", "Adam", "Manah"],
    "Ash Sharqiyah North": ["Ibra", "Al Mudaybi", "Sur"],
}

# ── Pakistan ──────────────────────────────────────────────────────────────────
PAKISTAN_PROVINCES: List[str] = [
    "Azad Jammu and Kashmir", "Balochistan", "Gilgit-Baltistan",
    "Islamabad Capital Territory", "Khyber Pakhtunkhwa",
    "Punjab", "Sindh",
]
PAKISTAN_DISTRICTS: Dict[str, List[str]] = {
    "Punjab": ["Lahore", "Faisalabad", "Rawalpindi", "Multan", "Gujranwala", "Sialkot"],
    "Sindh": ["Karachi", "Hyderabad", "Sukkur", "Larkana", "Nawabshah"],
    "Khyber Pakhtunkhwa": ["Peshawar", "Mardan", "Abbottabad", "Swat", "Dera Ismail Khan"],
    "Balochistan": ["Quetta", "Turbat", "Khuzdar", "Hub", "Gwadar"],
    "Islamabad Capital Territory": ["Islamabad City"],
    "Azad Jammu and Kashmir": ["Muzaffarabad", "Mirpur", "Rawalakot"],
    "Gilgit-Baltistan": ["Gilgit", "Skardu", "Chilas"],
}

# ── Palau ─────────────────────────────────────────────────────────────────────
PALAU_STATES: List[str] = [
    "Aimeliik", "Airai", "Angaur", "Hatohobei", "Kayangel",
    "Koror", "Melekeok", "Ngaraard", "Ngarchelong", "Ngardmau",
    "Ngatpang", "Ngchesar", "Ngeremlengui", "Ngiwal", "Peleliu",
    "Sonsorol",
]
PALAU_VILLAGES: Dict[str, List[str]] = {
    "Koror": ["Koror City"],
    "Melekeok": ["Ngerulmud (Capital)"],
    "Airai": ["Airai State"],
    "Peleliu": ["Peleliu State"],
    "Babeldaob": ["Babeldaob Island"],
}

# ── Palestine ─────────────────────────────────────────────────────────────────
PALESTINE_GOVERNORATES: List[str] = [
    "Bethlehem", "Deir el-Balah", "Gaza", "Hebron", "Jenin",
    "Jericho and Al Aghwar", "Jerusalem", "Khan Yunis", "Nablus",
    "North Gaza", "Qalqilya", "Rafah", "Ramallah and Al-Bireh",
    "Salfit", "Tubas", "Tulkarm",
]
PALESTINE_MUNICIPALITIES: Dict[str, List[str]] = {
    "Gaza": ["Gaza City"],
    "Jerusalem": ["East Jerusalem"],
    "Ramallah and Al-Bireh": ["Ramallah", "Al-Bireh"],
    "Nablus": ["Nablus City"],
    "Hebron": ["Hebron City"],
    "Jenin": ["Jenin City"],
    "Bethlehem": ["Bethlehem City"],
}

# ── Panama ────────────────────────────────────────────────────────────────────
PANAMA_PROVINCES: List[str] = [
    "Bocas del Toro", "Chiriquí", "Coclé", "Colón", "Darién",
    "Emberá-Wounaan", "Guna Yala", "Herrera", "Los Santos",
    "Ngäbe-Buglé", "Panamá", "Panamá Oeste", "Veraguas",
]
PANAMA_DISTRICTS: Dict[str, List[str]] = {
    "Panamá": ["Panama City", "Chepo", "Balboa", "San Miguelito"],
    "Panamá Oeste": ["La Chorrera", "Arraiján", "Capira", "Chame"],
    "Chiriquí": ["David", "Barú", "Boquete", "Bugaba"],
    "Coclé": ["Penonomé", "Aguadulce", "Natá", "Olá"],
    "Colón": ["Colón City", "Portobelo", "Santa Isabel"],
    "Herrera": ["Chitré", "Los Santos City", "Ocú"],
}

# ── Papua New Guinea ──────────────────────────────────────────────────────────
PAPUA_NEW_GUINEA_PROVINCES: List[str] = [
    "Bougainville", "Central", "Chimbu", "East New Britain",
    "East Sepik", "Eastern Highlands", "Enga", "Gulf",
    "Hela", "Jiwaka", "Madang", "Manus", "Milne Bay",
    "Morobe", "National Capital District", "New Ireland",
    "Northern (Oro)", "Southern Highlands", "West New Britain",
    "West Sepik", "Western", "Western Highlands",
]
PAPUA_NEW_GUINEA_DISTRICTS: Dict[str, List[str]] = {
    "National Capital District": ["Port Moresby"],
    "Morobe": ["Lae", "Huon Gulf", "Markham"],
    "Western Highlands": ["Mount Hagen", "Tambul-Nebilyer"],
    "East New Britain": ["Rabaul", "Kokopo", "Gazelle"],
    "East Sepik": ["Wewak", "Ambunti-Dreikikir"],
    "Madang": ["Madang Town", "Sumkar"],
    "Bougainville": ["Arawa", "Buka", "Panguna"],
}

# ── Paraguay ──────────────────────────────────────────────────────────────────
PARAGUAY_DEPARTMENTS: List[str] = [
    "Alto Paraguay", "Alto Paraná", "Amambay", "Asunción", "Boquerón",
    "Caaguazú", "Caazapá", "Canindeyú", "Central", "Concepción",
    "Cordillera", "Guairá", "Itapúa", "Misiones", "Ñeembucú",
    "Paraguarí", "Presidente Hayes", "San Pedro",
]
PARAGUAY_MUNICIPALITIES: Dict[str, List[str]] = {
    "Asunción": ["Asunción City"],
    "Central": ["Luque", "San Lorenzo", "Fernando de la Mora", "Lambaré", "Villa Elisa"],
    "Alto Paraná": ["Ciudad del Este", "Hernandarias", "Minga Guazú"],
    "Itapúa": ["Encarnación", "Hohenau", "Trinidad"],
    "Concepción": ["Concepción City", "Horqueta"],
}

# ── Peru ──────────────────────────────────────────────────────────────────────
PERU_REGIONS: List[str] = [
    "Amazonas", "Áncash", "Apurímac", "Arequipa", "Ayacucho",
    "Cajamarca", "Callao", "Cusco", "Huancavelica", "Huánuco",
    "Ica", "Junín", "La Libertad", "Lambayeque", "Lima",
    "Loreto", "Madre de Dios", "Moquegua", "Pasco", "Piura",
    "Puno", "San Martín", "Tacna", "Tumbes", "Ucayali",
]
PERU_PROVINCES: Dict[str, List[str]] = {
    "Lima": ["Lima City", "Callao City", "Huaral", "Cañete", "Huarochirí"],
    "Arequipa": ["Arequipa City", "Camaná", "Islay", "Caravelí"],
    "La Libertad": ["Trujillo", "Chepén", "Pacasmayo", "Ascope"],
    "Piura": ["Piura City", "Sullana", "Talara", "Morropón"],
    "Cusco": ["Cusco City", "Urubamba", "Calca", "Anta"],
    "Junín": ["Huancayo", "La Merced", "Tarma", "Jauja"],
    "Lambayeque": ["Chiclayo", "Ferreñafe", "Lambayeque City"],
}

# ── Philippines ───────────────────────────────────────────────────────────────
PHILIPPINES_REGIONS: List[str] = [
    "ARMM", "CAR", "Caraga", "MIMAROPA", "National Capital Region",
    "Region I (Ilocos Region)", "Region II (Cagayan Valley)",
    "Region III (Central Luzon)", "Region IV-A (Calabarzon)",
    "Region V (Bicol Region)", "Region VI (Western Visayas)",
    "Region VII (Central Visayas)", "Region VIII (Eastern Visayas)",
    "Region IX (Zamboanga Peninsula)", "Region X (Northern Mindanao)",
    "Region XI (Davao Region)", "Region XII (SOCCSKSARGEN)",
]
PHILIPPINES_PROVINCES: Dict[str, List[str]] = {
    "National Capital Region": ["Manila", "Quezon City", "Makati", "Pasig", "Taguig"],
    "Region IV-A (Calabarzon)": ["Cavite", "Laguna", "Batangas", "Rizal", "Quezon"],
    "Region III (Central Luzon)": ["Bulacan", "Pampanga", "Nueva Ecija", "Tarlac", "Zambales"],
    "Region VII (Central Visayas)": ["Cebu", "Bohol", "Negros Oriental", "Siquijor"],
    "Region XI (Davao Region)": ["Davao del Sur", "Davao del Norte", "Davao Oriental", "Davao Occidental"],
    "Region VI (Western Visayas)": ["Iloilo", "Negros Occidental", "Capiz", "Aklan", "Antique"],
    "Region X (Northern Mindanao)": ["Misamis Oriental", "Bukidnon", "Lanao del Norte"],
}

# ── Poland ────────────────────────────────────────────────────────────────────
POLAND_VOIVODESHIPS: List[str] = [
    "Greater Poland", "Holy Cross", "Kuyavian-Pomeranian",
    "Lesser Poland", "Łódź", "Lower Silesian", "Lublin",
    "Lubusz", "Masovian", "Opole", "Podlaskie", "Pomeranian",
    "Silesian", "Subcarpathian", "Warmian-Masurian", "West Pomeranian",
]
POLAND_COUNTIES: Dict[str, List[str]] = {
    "Masovian": ["Warsaw", "Radom", "Płock", "Siedlce", "Ostrołęka"],
    "Silesian": ["Katowice", "Sosnowiec", "Gliwice", "Bytom", "Zabrze"],
    "Lesser Poland": ["Kraków", "Tarnów", "Nowy Sącz", "Bielsko-Biała"],
    "Greater Poland": ["Poznań", "Kalisz", "Konin", "Piła", "Ostrów Wielkopolski"],
    "Lower Silesian": ["Wrocław", "Wałbrzych", "Legnica", "Jelenia Góra"],
    "Pomeranian": ["Gdańsk", "Gdynia", "Sopot", "Słupsk"],
    "Łódź": ["Łódź City", "Piotrków Trybunalski", "Skierniewice"],
    "Kuyavian-Pomeranian": ["Bydgoszcz", "Toruń", "Włocławek"],
}

# ── Qatar ─────────────────────────────────────────────────────────────────────
QATAR_MUNICIPALITIES: List[str] = [
    "Ad Dawhah", "Al Khor", "Al Rayyan", "Al Shahaniyah",
    "Al Shamal", "Al Wakrah", "Ash Shamal", "Doha",
    "Madinat ash Shamal", "Umm Salal",
]
QATAR_ZONES: Dict[str, List[str]] = {
    "Doha": ["Doha City", "West Bay", "Al Sadd", "Msheireb", "The Pearl"],
    "Al Rayyan": ["Al Rayyan City", "Al Aziziyah", "Muaither"],
    "Al Wakrah": ["Al Wakrah City", "Al Wukair"],
    "Al Khor": ["Al Khor City", "Al Dhakhira"],
    "Umm Salal": ["Umm Salal Muhammad"],
}

# ── Romania ───────────────────────────────────────────────────────────────────
ROMANIA_COUNTIES: List[str] = [
    "Alba", "Arad", "Argeș", "Bacău", "Bihor", "Bistrița-Năsăud",
    "Botoșani", "Brăila", "Brașov", "Bucharest", "Buzău",
    "Călărași", "Caraș-Severin", "Cluj", "Constanța", "Covasna",
    "Dâmbovița", "Dolj", "Galați", "Giurgiu", "Gorj",
    "Harghita", "Hunedoara", "Ialomița", "Iași", "Ilfov",
    "Maramureș", "Mehedinți", "Mureș", "Neamț", "Olt",
    "Prahova", "Sălaj", "Satu Mare", "Sibiu", "Suceava",
    "Teleorman", "Timiș", "Tulcea", "Vâlcea", "Vaslui",
    "Vrancea",
]
ROMANIA_CITIES: Dict[str, List[str]] = {
    "Bucharest": ["Bucharest City"],
    "Cluj": ["Cluj-Napoca", "Dej", "Turda", "Câmpia Turzii"],
    "Timiș": ["Timișoara", "Lugoj", "Jimbolia"],
    "Iași": ["Iași City", "Pașcani", "Hârlău"],
    "Constanța": ["Constanța City", "Mangalia", "Cernavodă"],
    "Prahova": ["Ploiești", "Câmpina", "Sinaia", "Bușteni"],
    "Brașov": ["Brașov City", "Codlea", "Săcele", "Predeal"],
}

# ── Russia ────────────────────────────────────────────────────────────────────
RUSSIA_FEDERAL_SUBJECTS: List[str] = [
    "Altai Krai", "Altai Republic", "Amur Oblast", "Arkhangelsk Oblast",
    "Astrakhan Oblast", "Bashkortostan", "Belgorod Oblast", "Bryansk Oblast",
    "Buryatia", "Chechen Republic", "Chelyabinsk Oblast", "Chukotka",
    "Chuvashia", "Dagestan", "Ingushetia", "Irkutsk Oblast",
    "Ivanovo Oblast", "Jewish Autonomous Oblast", "Kabardino-Balkaria",
    "Kaliningrad Oblast", "Kalmykia", "Kaluga Oblast", "Kamchatka Krai",
    "Karachay-Cherkessia", "Karelia", "Kemerovo Oblast", "Khabarovsk Krai",
    "Khakassia", "Khanty-Mansi", "Kirov Oblast", "Komi Republic",
    "Kostroma Oblast", "Krasnodar Krai", "Krasnoyarsk Krai", "Kurgan Oblast",
    "Kursk Oblast", "Leningrad Oblast", "Lipetsk Oblast", "Magadan Oblast",
    "Mari El", "Mordovia", "Moscow", "Moscow Oblast", "Murmansk Oblast",
    "Nenets Autonomous Okrug", "Nizhny Novgorod Oblast", "North Ossetia",
    "Novgorod Oblast", "Novosibirsk Oblast", "Omsk Oblast", "Orel Oblast",
    "Orenburg Oblast", "Penza Oblast", "Perm Krai", "Primorsky Krai",
    "Pskov Oblast", "Rostov Oblast", "Ryazan Oblast", "Saint Petersburg",
    "Sakha Republic", "Sakhalin Oblast", "Samara Oblast", "Saratov Oblast",
    "Smolensk Oblast", "Stavropol Krai", "Sverdlovsk Oblast", "Tambov Oblast",
    "Tatarstan", "Tomsk Oblast", "Tula Oblast", "Tuva", "Tver Oblast",
    "Tyumen Oblast", "Udmurtia", "Ulyanovsk Oblast", "Vladimir Oblast",
    "Volgograd Oblast", "Vologda Oblast", "Voronezh Oblast",
    "Yamalo-Nenets", "Yaroslavl Oblast", "Zabaykalsky Krai",
]
RUSSIA_CITIES: Dict[str, List[str]] = {
    "Moscow": ["Moscow City", "Zelenograd", "Troitsk", "Shcherbinka"],
    "Saint Petersburg": ["Saint Petersburg City", "Peterhof", "Pushkin"],
    "Tatarstan": ["Kazan", "Naberezhnye Chelny", "Nizhnekamsk", "Almetyevsk"],
    "Sverdlovsk Oblast": ["Yekaterinburg", "Nizhny Tagil", "Kamensk-Uralsky"],
    "Novosibirsk Oblast": ["Novosibirsk", "Berdsk", "Ob"],
    "Krasnodar Krai": ["Krasnodar", "Sochi", "Novorossiysk", "Armavir"],
    "Krasnoyarsk Krai": ["Krasnoyarsk", "Norilsk", "Achinsk"],
    "Rostov Oblast": ["Rostov-on-Don", "Taganrog", "Shakhty", "Volgodonsk"],
}

# ── Saint Kitts and Nevis ─────────────────────────────────────────────────────
SAINT_KITTS_NEVIS_PARISHES: List[str] = [
    "Christ Church Nichola Town", "Saint Anne Sandy Point",
    "Saint George Basseterre", "Saint George Gingerland",
    "Saint James Windward", "Saint John Capesterre",
    "Saint John Figtree", "Saint Mary Cayon", "Saint Paul Capesterre",
    "Saint Paul Charlestown", "Saint Peter Basseterre",
    "Saint Thomas Lowland", "Saint Thomas Middle Island",
    "Trinity Palmetto Point",
]
SAINT_KITTS_NEVIS_VILLAGES: Dict[str, List[str]] = {
    "Saint George Basseterre": ["Basseterre"],
    "Saint Paul Charlestown": ["Charlestown"],
    "Saint Peter Basseterre": ["Bird Rock"],
    "Saint Anne Sandy Point": ["Sandy Point"],
    "Saint Thomas Middle Island": ["Middle Island"],
}

# ── Saint Lucia ───────────────────────────────────────────────────────────────
SAINT_LUCIA_DISTRICTS: List[str] = [
    "Anse la Raye", "Canaries", "Castries", "Choiseul", "Dennery",
    "Gros Islet", "Laborie", "Micoud", "Soufrière", "Vieux Fort",
]
SAINT_LUCIA_VILLAGES: Dict[str, List[str]] = {
    "Castries": ["Castries City", "Gros Islet Town"],
    "Vieux Fort": ["Vieux Fort Town"],
    "Soufrière": ["Soufrière Town"],
    "Micoud": ["Micoud Village"],
    "Dennery": ["Dennery Village"],
}

# ── Saint Vincent and the Grenadines ─────────────────────────────────────────
SAINT_VINCENT_PARISHES: List[str] = [
    "Charlotte", "Grenadines", "Saint Andrew", "Saint David",
    "Saint George", "Saint Patrick",
]
SAINT_VINCENT_VILLAGES: Dict[str, List[str]] = {
    "Saint George": ["Kingstown"],
    "Charlotte": ["Georgetown"],
    "Grenadines": ["Port Elizabeth", "Clifton"],
    "Saint Patrick": ["Barrouallie"],
    "Saint Andrew": ["Colonarie"],
}

# ── Samoa ─────────────────────────────────────────────────────────────────────
SAMOA_DISTRICTS: List[str] = [
    "A'ana", "Aiga-i-le-Tai", "Atua", "Fa'asaleleaga", "Gaga'emauga",
    "Gagaifomauga", "Palauli", "Satupa'itea", "Tuamasaga", "Va'a-o-Fonoti",
    "Vaisigano",
]
SAMOA_VILLAGES: Dict[str, List[str]] = {
    "Tuamasaga": ["Apia", "Faleula", "Vailima"],
    "A'ana": ["Leulumoega", "Nofoalii"],
    "Atua": ["Lufilufi", "Solosolo"],
    "Fa'asaleleaga": ["Saleologa", "Lalomalava"],
    "Palauli": ["Palauli", "Samalaeulu"],
}

# ── San Marino ────────────────────────────────────────────────────────────────
SAN_MARINO_CASTLES: List[str] = [
    "Acquaviva", "Borgo Maggiore", "Chiesanuova", "Domagnano",
    "Faetano", "Fiorentino", "Montegiardino", "San Marino City",
    "Serravalle",
]
SAN_MARINO_LOCALITIES: Dict[str, List[str]] = {
    "San Marino City": ["San Marino City"],
    "Serravalle": ["Serravalle", "Dogana"],
    "Borgo Maggiore": ["Borgo Maggiore"],
    "Domagnano": ["Domagnano"],
    "Fiorentino": ["Fiorentino"],
}

# ── Saudi Arabia ──────────────────────────────────────────────────────────────
SAUDI_ARABIA_REGIONS: List[str] = [
    "Al Bahah", "Al Jawf", "Al Madinah", "Al Qassim", "Asir",
    "Eastern Province", "Ha'il", "Jizan", "Mecca", "Najran",
    "Northern Borders", "Riyadh", "Tabuk",
]
SAUDI_ARABIA_GOVERNORATES: Dict[str, List[str]] = {
    "Riyadh": ["Riyadh City", "Ad Diriyah", "Al Kharj", "Marat", "Dawadmi"],
    "Mecca": ["Jeddah", "Mecca City", "Taif", "Yanbu"],
    "Eastern Province": ["Dammam", "Al-Ahsa", "Dhahran", "Al Khobar", "Jubail"],
    "Al Madinah": ["Medina City", "Yanbu City", "Mahd adh Dhahab"],
    "Asir": ["Abha", "Khamis Mushait", "Jizan City", "Najran City"],
    "Jizan": ["Jizan City", "Sabya", "Samtah"],
}

# ── Serbia ────────────────────────────────────────────────────────────────────
SERBIA_DISTRICTS: List[str] = [
    "Belgrade", "Bor", "Braničevo", "Jablanica", "Kolubara",
    "Mačva", "Moravica", "Nišava", "Pčinja", "Pirot", "Podunavlje",
    "Pomoravlje", "Rasina", "Raška", "Šumadija", "Toplica",
    "Vojvodina - South Bačka", "Vojvodina - North Bačka",
    "Vojvodina - West Bačka", "Vojvodina - South Banat",
    "Vojvodina - North Banat", "Vojvodina - Central Banat",
    "Vojvodina - Srem", "Zaječar", "Zlatibor",
]
SERBIA_MUNICIPALITIES: Dict[str, List[str]] = {
    "Belgrade": ["Belgrade City", "Zemun", "Novi Beograd", "Rakovica", "Palilula"],
    "Vojvodina - South Bačka": ["Novi Sad", "Subotica", "Sombor", "Zrenjanin"],
    "Nišava": ["Niš", "Pirot City", "Prokuplje"],
    "Šumadija": ["Kragujevac", "Topola", "Rača"],
    "Rasina": ["Kruševac", "Aleksandrovac"],
    "Zlatibor": ["Užice", "Čačak", "Požega"],
}

# ── Singapore ─────────────────────────────────────────────────────────────────
SINGAPORE_REGIONS: List[str] = [
    "Central Region", "East Region", "North Region",
    "North-East Region", "West Region",
]
SINGAPORE_PLANNING_AREAS: Dict[str, List[str]] = {
    "Central Region": ["Downtown Core", "Marina Bay", "Orchard", "Newton", "Tanglin", "Bishan"],
    "North Region": ["Woodlands", "Sembawang", "Yishun", "Mandai"],
    "North-East Region": ["Punggol", "Sengkang", "Hougang", "Serangoon"],
    "East Region": ["Tampines", "Pasir Ris", "Bedok", "Changi"],
    "West Region": ["Jurong East", "Jurong West", "Bukit Batok", "Clementi", "Choa Chu Kang"],
}

# ── Slovakia ──────────────────────────────────────────────────────────────────
SLOVAKIA_REGIONS: List[str] = [
    "Banská Bystrica Region", "Bratislava Region", "Košice Region",
    "Nitra Region", "Prešov Region", "Trenčín Region",
    "Trnava Region", "Žilina Region",
]
SLOVAKIA_DISTRICTS: Dict[str, List[str]] = {
    "Bratislava Region": ["Bratislava City", "Malacky", "Pezinok", "Senec"],
    "Košice Region": ["Košice City", "Spišská Nová Ves", "Rožňava"],
    "Banská Bystrica Region": ["Banská Bystrica City", "Zvolen", "Rimavská Sobota"],
    "Prešov Region": ["Prešov City", "Poprad", "Stará Ľubovňa"],
    "Nitra Region": ["Nitra City", "Komárno", "Šaľa"],
    "Žilina Region": ["Žilina City", "Martin", "Čadca"],
}

# ── Slovenia ──────────────────────────────────────────────────────────────────
SLOVENIA_STATISTICAL_REGIONS: List[str] = [
    "Central Slovenia", "Coastal-Karst", "Gorenjska", "Goriška",
    "Koroška", "Littoral-Inner Carniola", "Lower Sava",
    "Obalno-kraška", "Pomurje", "Posavje", "Savinja", "Southeast Slovenia",
    "Štajerska", "Upper Carniola", "Zasavje",
]
SLOVENIA_MUNICIPALITIES: Dict[str, List[str]] = {
    "Central Slovenia": ["Ljubljana", "Domžale", "Kamnik", "Grosuplje"],
    "Gorenjska": ["Kranj", "Škofja Loka", "Jesenice", "Tržič"],
    "Savinja": ["Celje", "Velenje", "Žalec"],
    "Koroška": ["Slovenj Gradec", "Ravne na Koroškem", "Dravograd"],
    "Coastal-Karst": ["Koper", "Piran", "Portorož", "Izola"],
    "Pomurje": ["Murska Sobota", "Ljutomer"],
}

# ── Solomon Islands ───────────────────────────────────────────────────────────
SOLOMON_ISLANDS_PROVINCES: List[str] = [
    "Capital Territory (Honiara)", "Central Province", "Choiseul Province",
    "Guadalcanal Province", "Isabel Province", "Makira-Ulawa Province",
    "Malaita Province", "Rennell and Bellona Province",
    "Temotu Province", "Western Province",
]
SOLOMON_ISLANDS_CONSTITUENCIES: Dict[str, List[str]] = {
    "Capital Territory (Honiara)": ["Honiara City"],
    "Guadalcanal Province": ["Gold Ridge", "North Guadalcanal", "South Guadalcanal"],
    "Malaita Province": ["Auki", "North Malaita", "South Malaita"],
    "Western Province": ["Gizo", "Munda", "Noro"],
    "Central Province": ["Tulagi", "Russell Islands"],
}

# ── Sri Lanka ─────────────────────────────────────────────────────────────────
SRI_LANKA_PROVINCES: List[str] = [
    "Central Province", "Eastern Province", "North Central Province",
    "North Western Province", "Northern Province", "Sabaragamuwa Province",
    "Southern Province", "Uva Province", "Western Province",
]
SRI_LANKA_DISTRICTS: Dict[str, List[str]] = {
    "Western Province": ["Colombo", "Gampaha", "Kalutara"],
    "Central Province": ["Kandy", "Matale", "Nuwara Eliya"],
    "Southern Province": ["Galle", "Matara", "Hambantota"],
    "Northern Province": ["Jaffna", "Kilinochchi", "Mannar", "Mullaitivu", "Vavuniya"],
    "Eastern Province": ["Ampara", "Batticaloa", "Trincomalee"],
    "North Western Province": ["Kurunegala", "Puttalam"],
    "Uva Province": ["Badulla", "Monaragala"],
    "Sabaragamuwa Province": ["Kegalle", "Ratnapura"],
    "North Central Province": ["Anuradhapura", "Polonnaruwa"],
}

# ── Suriname ──────────────────────────────────────────────────────────────────
SURINAME_DISTRICTS: List[str] = [
    "Brokopondo", "Commewijne", "Coronie", "Marowijne",
    "Nickerie", "Para", "Paramaribo", "Saramacca",
    "Sipaliwini", "Wanica",
]
SURINAME_RESORTS: Dict[str, List[str]] = {
    "Paramaribo": ["Paramaribo City", "Livorno", "Beekhuizen"],
    "Wanica": ["Lelydorp", "Uitvlugt"],
    "Nickerie": ["Nieuw Nickerie", "Wageningen"],
    "Commewijne": ["Nieuw Amsterdam", "Meerzorg"],
    "Saramacca": ["Groningen", "Uitkijk"],
}

# ── Sweden ────────────────────────────────────────────────────────────────────
SWEDEN_COUNTIES: List[str] = [
    "Blekinge County", "Dalarna County", "Gävleborg County", "Gotland County",
    "Halland County", "Jämtland County", "Jönköping County", "Kalmar County",
    "Kronoberg County", "Norrbotten County", "Örebro County", "Östergötland County",
    "Skåne County", "Södermanland County", "Stockholm County", "Uppsala County",
    "Värmland County", "Västerbotten County", "Västernorrland County",
    "Västmanland County", "Västra Götaland County",
]
SWEDEN_MUNICIPALITIES: Dict[str, List[str]] = {
    "Stockholm County": ["Stockholm City", "Huddinge", "Järfälla", "Solna", "Haninge"],
    "Västra Götaland County": ["Gothenburg", "Mölndal", "Borås", "Trollhättan"],
    "Skåne County": ["Malmö", "Helsingborg", "Kristianstad", "Lund"],
    "Östergötland County": ["Linköping", "Norrköping", "Motala"],
    "Uppsala County": ["Uppsala City", "Enköping"],
    "Jönköping County": ["Jönköping City", "Huskvarna", "Nässjö"],
    "Norrbotten County": ["Luleå", "Piteå", "Boden", "Kiruna"],
}

# ── Syria ─────────────────────────────────────────────────────────────────────
SYRIA_GOVERNORATES: List[str] = [
    "Al-Hasakah", "Al-Raqqah", "Aleppo", "As-Suwayda", "Damascus",
    "Daraa", "Deir ez-Zor", "Hama", "Homs", "Idlib", "Latakia",
    "Quneitra", "Rif Dimashq", "Tartus",
]
SYRIA_DISTRICTS: Dict[str, List[str]] = {
    "Damascus": ["Damascus City"],
    "Aleppo": ["Aleppo City", "Al-Bab", "Azaz", "Afrin"],
    "Homs": ["Homs City", "Palmyra", "Al-Qusayr"],
    "Hama": ["Hama City", "Masyaf", "Salamiyah"],
    "Latakia": ["Latakia City", "Jableh", "Al-Haffah"],
    "Idlib": ["Idlib City", "Maaret al-Numan", "Jisr al-Shughur"],
    "Rif Dimashq": ["Douma", "Al-Qaboun", "Darayya"],
    "Daraa": ["Daraa City", "Bosra"],
}

# ── Taiwan ────────────────────────────────────────────────────────────────────
TAIWAN_COUNTIES_CITIES: List[str] = [
    "Changhua County", "Chiayi City", "Chiayi County", "Hsinchu City",
    "Hsinchu County", "Hualien County", "Kaohsiung City", "Keelung City",
    "Kinmen County", "Lienchiang County", "Miaoli County", "Nantou County",
    "New Taipei City", "Penghu County", "Pingtung County", "Taichung City",
    "Tainan City", "Taipei City", "Taitung County", "Taoyuan City",
    "Yilan County", "Yunlin County",
]
TAIWAN_TOWNSHIPS: Dict[str, List[str]] = {
    "Taipei City": ["Zhongzheng", "Da'an", "Zhongshan", "Xinyi", "Shilin"],
    "New Taipei City": ["Banqiao", "Sanchong", "Yonghe", "Zhonghe", "Xindian"],
    "Taichung City": ["Taichung Central", "Beitun", "Xitun", "Nantun"],
    "Kaohsiung City": ["Lingya", "Xinxing", "Zuoying", "Sanmin", "Gushan"],
    "Tainan City": ["East District", "West District", "Anping", "Annan"],
    "Taoyuan City": ["Taoyuan District", "Zhongli", "Pingzhen"],
}

# ── Tajikistan ────────────────────────────────────────────────────────────────
TAJIKISTAN_REGIONS: List[str] = [
    "Dushanbe City", "Gorno-Badakhshan", "Khatlon", "Regions of Republican Subordination",
    "Sughd",
]
TAJIKISTAN_DISTRICTS: Dict[str, List[str]] = {
    "Dushanbe City": ["Dushanbe City"],
    "Sughd": ["Khujand", "Istaravshan", "Panjakent", "Isfara"],
    "Khatlon": ["Bokhtar", "Kulob", "Qurghonteppa"],
    "Gorno-Badakhshan": ["Khorugh", "Ishkoshim", "Rushan"],
    "Regions of Republican Subordination": ["Vahdat", "Tursunzoda", "Hisor"],
}

# ── Thailand ──────────────────────────────────────────────────────────────────
THAILAND_PROVINCES: List[str] = [
    "Amnat Charoen", "Ang Thong", "Bangkok", "Bueng Kan", "Buri Ram",
    "Chachoengsao", "Chai Nat", "Chaiyaphum", "Chanthaburi", "Chiang Mai",
    "Chiang Rai", "Chon Buri", "Chumphon", "Kalasin", "Kamphaeng Phet",
    "Kanchanaburi", "Khon Kaen", "Krabi", "Lampang", "Lamphun",
    "Loei", "Lop Buri", "Mae Hong Son", "Maha Sarakham", "Mukdahan",
    "Nakhon Nayok", "Nakhon Pathom", "Nakhon Phanom", "Nakhon Ratchasima",
    "Nakhon Sawan", "Nakhon Si Thammarat", "Nan", "Narathiwat",
    "Nong Bua Lam Phu", "Nong Khai", "Nonthaburi", "Pathum Thani",
    "Pattani", "Phang Nga", "Phatthalung", "Phayao", "Phetchabun",
    "Phetchaburi", "Phichit", "Phitsanulok", "Phra Nakhon Si Ayutthaya",
    "Phrae", "Phuket", "Prachin Buri", "Prachuap Khiri Khan", "Ranong",
    "Ratchaburi", "Rayong", "Roi Et", "Sa Kaeo", "Sakon Nakhon",
    "Samut Prakan", "Samut Sakhon", "Samut Songkhram", "Saraburi",
    "Satun", "Sing Buri", "Si Sa Ket", "Songkhla", "Sukhothai",
    "Suphanburi", "Surat Thani", "Surin", "Tak", "Trang",
    "Trat", "Ubon Ratchathani", "Udon Thani", "Uthai Thani",
    "Uttaradit", "Yala", "Yasothon",
]
THAILAND_DISTRICTS: Dict[str, List[str]] = {
    "Bangkok": ["Phra Nakhon", "Dusit", "Pathum Wan", "Bang Rak", "Watthana"],
    "Chiang Mai": ["Mueang Chiang Mai", "Hang Dong", "San Sai", "Mae Rim"],
    "Chon Buri": ["Mueang Chon Buri", "Pattaya", "Si Racha", "Bang Lamung"],
    "Nakhon Ratchasima": ["Mueang Nakhon Ratchasima", "Pak Chong", "Bua Yai"],
    "Phuket": ["Mueang Phuket", "Kathu", "Thalang"],
    "Khon Kaen": ["Mueang Khon Kaen", "Nam Phong", "Chum Phae"],
    "Songkhla": ["Hat Yai", "Mueang Songkhla", "Na Thawi"],
}

# ── Timor-Leste ───────────────────────────────────────────────────────────────
TIMOR_LESTE_MUNICIPALITIES: List[str] = [
    "Aileu", "Ainaro", "Baucau", "Bobonaro", "Cova Lima",
    "Dili", "Ermera", "Lautem", "Liquiçá", "Manatuto",
    "Manufahi", "Oecusse", "Viqueque",
]
TIMOR_LESTE_ADMINISTRATIVE_POSTS: Dict[str, List[str]] = {
    "Dili": ["Vera Cruz", "Dom Aleixo", "Nain Feto", "Cristo Rei"],
    "Baucau": ["Baucau Town", "Laga", "Venilale", "Quelicai"],
    "Ermera": ["Ermera Town", "Atsabe", "Hatulia"],
    "Bobonaro": ["Maliana", "Balibo", "Atabae"],
    "Oecusse": ["Oecusse Town", "Passabe", "Nitibe"],
}

# ── Tonga ─────────────────────────────────────────────────────────────────────
TONGA_DIVISIONS: List[str] = [
    "Ha'apai", "Tongatapu", "Vava'u", "'Eua", "Ongo Niua",
]
TONGA_ISLANDS: Dict[str, List[str]] = {
    "Tongatapu": ["Nuku'alofa", "Mu'a", "Lapaha", "Neiafu"],
    "Vava'u": ["Neiafu", "Pangaimotu"],
    "Ha'apai": ["Pangai", "Ha'afeva"],
    "'Eua": ["'Ohonua", "Futu"],
    "Ongo Niua": ["Niuafo'ou", "Niuatoputapu"],
}

# ── Trinidad and Tobago ───────────────────────────────────────────────────────
TRINIDAD_TOBAGO_REGIONS: List[str] = [
    "Arima", "Chaguanas", "Couva-Tabaquite-Talparo", "Diego Martin",
    "Gulf of Paria", "Mayaro-Rio Claro", "Penal-Debe", "Point Fortin",
    "Port of Spain", "Princes Town", "San Fernando", "San Juan-Laventille",
    "Sangre Grande", "Siparia", "Tobago", "Tunapuna-Piarco",
]
TRINIDAD_TOBAGO_COMMUNITIES: Dict[str, List[str]] = {
    "Port of Spain": ["Port of Spain City"],
    "San Fernando": ["San Fernando City"],
    "Chaguanas": ["Chaguanas Borough"],
    "Tobago": ["Scarborough", "Plymouth", "Speyside"],
    "Arima": ["Arima Borough"],
    "Tunapuna-Piarco": ["Tunapuna", "Piarco", "St. Augustine"],
}

# ── Türkiye ────────────────────────────────────────────────────────────────────
TURKEY_PROVINCES: List[str] = [
    "Adana", "Adıyaman", "Afyonkarahisar", "Ağrı", "Aksaray",
    "Amasya", "Ankara", "Antalya", "Ardahan", "Artvin",
    "Aydın", "Balıkesir", "Bartın", "Batman", "Bayburt",
    "Bilecik", "Bingöl", "Bitlis", "Bolu", "Burdur",
    "Bursa", "Çanakkale", "Çankırı", "Çorum", "Denizli",
    "Diyarbakır", "Düzce", "Edirne", "Elazığ", "Erzincan",
    "Erzurum", "Eskişehir", "Gaziantep", "Giresun", "Gümüşhane",
    "Hakkari", "Hatay", "Iğdır", "Isparta", "Istanbul",
    "İzmir", "Kahramanmaraş", "Karabük", "Karaman", "Kars",
    "Kastamonu", "Kayseri", "Kırıkkale", "Kırklareli", "Kırşehir",
    "Kilis", "Kocaeli", "Konya", "Kütahya", "Malatya",
    "Manisa", "Mardin", "Mersin", "Muğla", "Muş",
    "Nevşehir", "Niğde", "Ordu", "Osmaniye", "Rize",
    "Sakarya", "Samsun", "Şanlıurfa", "Siirt", "Sinop",
    "Sivas", "Şırnak", "Tekirdağ", "Tokat", "Trabzon",
    "Tunceli", "Uşak", "Van", "Yalova", "Yozgat", "Zonguldak",
]
TURKEY_DISTRICTS: Dict[str, List[str]] = {
    "Istanbul": ["Fatih", "Beyoğlu", "Beşiktaş", "Kadıköy", "Üsküdar", "Bakırköy"],
    "Ankara": ["Çankaya", "Keçiören", "Mamak", "Yenimahalle", "Altındağ"],
    "İzmir": ["Konak", "Bornova", "Karşıyaka", "Buca", "Çiğli"],
    "Antalya": ["Muratpaşa", "Konyaaltı", "Kepez", "Serik"],
    "Bursa": ["Osmangazi", "Yıldırım", "Nilüfer", "Gemlik"],
    "Adana": ["Seyhan", "Yüreğir", "Çukurova", "Sarıçam"],
    "Gaziantep": ["Şahinbey", "Şehitkamil", "Nizip"],
}

# ── Turkmenistan ──────────────────────────────────────────────────────────────
TURKMENISTAN_PROVINCES: List[str] = [
    "Ahal", "Ashgabat", "Balkan", "Daşoguz", "Lebap", "Mary",
]
TURKMENISTAN_DISTRICTS: Dict[str, List[str]] = {
    "Ashgabat": ["Ashgabat City"],
    "Ahal": ["Abadan", "Ak Bugday", "Babadayhany", "Büzmeyin"],
    "Balkan": ["Turkmenbashi", "Balkanabat", "Gumdag", "Serdar"],
    "Daşoguz": ["Daşoguz City", "Gurbansoltan Eje", "Köneürgench"],
    "Lebap": ["Türkmenabat", "Farap", "Halaç", "Çärjew"],
    "Mary": ["Mary City", "Bayramaly", "Yolöten", "Tagtabazar"],
}

# ── Tuvalu ────────────────────────────────────────────────────────────────────
TUVALU_ISLANDS: List[str] = [
    "Funafuti", "Nanumanga", "Nanumea", "Niulakita", "Niutao",
    "Nui", "Nukufetau", "Nukulaelae", "Vaitupu",
]
TUVALU_VILLAGES: Dict[str, List[str]] = {
    "Funafuti": ["Fongafale", "Senala", "Alapi"],
    "Vaitupu": ["Asau"],
    "Nanumea": ["Lolua"],
    "Nanumanga": ["Tonga"],
    "Niutao": ["Kulia"],
}

# ── Ukraine ───────────────────────────────────────────────────────────────────
UKRAINE_OBLASTS: List[str] = [
    "Cherkasy Oblast", "Chernihiv Oblast", "Chernivtsi Oblast",
    "Crimea Republic", "Dnipropetrovsk Oblast", "Donetsk Oblast",
    "Ivano-Frankivsk Oblast", "Kharkiv Oblast", "Kherson Oblast",
    "Khmelnytskyi Oblast", "Kirovohrad Oblast", "Kyiv City",
    "Kyiv Oblast", "Luhansk Oblast", "Lviv Oblast", "Mykolaiv Oblast",
    "Odessa Oblast", "Poltava Oblast", "Rivne Oblast", "Sumy Oblast",
    "Ternopil Oblast", "Vinnytsia Oblast", "Volyn Oblast",
    "Zakarpattia Oblast", "Zaporizhzhia Oblast", "Zhytomyr Oblast",
]
UKRAINE_DISTRICTS: Dict[str, List[str]] = {
    "Kyiv City": ["Kyiv City"],
    "Kyiv Oblast": ["Brovary", "Boryspil", "Vasylkiv", "Bucha", "Irpin"],
    "Lviv Oblast": ["Lviv City", "Stryi", "Drohobych", "Boryslav"],
    "Kharkiv Oblast": ["Kharkiv City", "Poltava City", "Sumy City"],
    "Odessa Oblast": ["Odessa City", "Mykolaiv City", "Kherson City"],
    "Dnipropetrovsk Oblast": ["Dnipro City", "Kryvyi Rih", "Kamianske"],
    "Donetsk Oblast": ["Donetsk City", "Mariupol", "Kramatorsk", "Sloviansk"],
}

# ── Uruguay ───────────────────────────────────────────────────────────────────
URUGUAY_DEPARTMENTS: List[str] = [
    "Artigas", "Canelones", "Cerro Largo", "Colonia", "Durazno",
    "Flores", "Florida", "Lavalleja", "Maldonado", "Montevideo",
    "Paysandú", "Río Negro", "Rivera", "Rocha", "Salto",
    "San José", "Soriano", "Tacuarembó", "Treinta y Tres",
]
URUGUAY_MUNICIPALITIES: Dict[str, List[str]] = {
    "Montevideo": ["Montevideo City", "Las Piedras", "Paysandú City"],
    "Canelones": ["Las Piedras", "Canelones City", "La Paz", "Santa Lucía"],
    "Maldonado": ["Maldonado City", "Punta del Este", "San Carlos"],
    "Salto": ["Salto City", "Artigas City"],
    "Colonia": ["Colonia del Sacramento", "Mercedes", "Carmelo"],
}

# ── Uzbekistan ────────────────────────────────────────────────────────────────
UZBEKISTAN_REGIONS: List[str] = [
    "Andijan Region", "Bukhara Region", "Fergana Region",
    "Jizzakh Region", "Karakalpakstan", "Kashkadarya Region",
    "Khorezm Region", "Namangan Region", "Navoiy Region",
    "Samarkand Region", "Sirdaryo Region", "Surkhandarya Region",
    "Tashkent City", "Tashkent Region",
]
UZBEKISTAN_DISTRICTS: Dict[str, List[str]] = {
    "Tashkent City": ["Tashkent City"],
    "Tashkent Region": ["Angren", "Chirchiq", "Bekabad", "Nurafshon"],
    "Samarkand Region": ["Samarkand City", "Kattakurgan", "Urgut"],
    "Fergana Region": ["Fergana City", "Margilan", "Quvasoy", "Kokand"],
    "Andijan Region": ["Andijan City", "Asaka", "Shahrixon"],
    "Namangan Region": ["Namangan City", "Kosonsoy", "Pop", "Uychi"],
    "Bukhara Region": ["Bukhara City", "Navoiy City", "Qarshi"],
}

# ── Vanuatu ───────────────────────────────────────────────────────────────────
VANUATU_PROVINCES: List[str] = [
    "Malampa", "Penama", "Sanma", "Shefa", "Tafea", "Torba",
]
VANUATU_AREAS: Dict[str, List[str]] = {
    "Shefa": ["Port Vila", "Efate", "Shepherd Islands"],
    "Sanma": ["Luganville", "Santo", "Malo"],
    "Malampa": ["Lakatoro", "Malekula", "Ambrym"],
    "Tafea": ["Isangel", "Tanna", "Aniwa"],
    "Penama": ["Saratamata", "Ambae", "Maewo", "Pentecost"],
    "Torba": ["Sola", "Gaua", "Torres Islands"],
}

# ── Vatican City ──────────────────────────────────────────────────────────────
VATICAN_QUARTERS: List[str] = [
    "Vatican City State",
]
VATICAN_ADMINISTRATIVE_UNITS: Dict[str, List[str]] = {
    "Vatican City State": ["Vatican City"],
}

# ── Venezuela ─────────────────────────────────────────────────────────────────
VENEZUELA_STATES: List[str] = [
    "Amazonas", "Anzoátegui", "Apure", "Aragua", "Barinas",
    "Bolívar", "Carabobo", "Cojedes", "Delta Amacuro", "Dependencias Federales",
    "Distrito Capital", "Falcón", "Guárico", "Lara", "Mérida",
    "Miranda", "Monagas", "Nueva Esparta", "Portuguesa", "Sucre",
    "Táchira", "Trujillo", "Vargas", "Yaracuy", "Zulia",
]
VENEZUELA_MUNICIPALITIES: Dict[str, List[str]] = {
    "Distrito Capital": ["Caracas City"],
    "Miranda": ["Baruta", "Chacao", "El Hatillo", "Sucre"],
    "Zulia": ["Maracaibo", "San Francisco", "Cabimas", "Ciudad Ojeda"],
    "Carabobo": ["Valencia", "Naguanagua", "San Diego", "Los Guayos"],
    "Lara": ["Barquisimeto", "Iribarren", "Concepción", "Jiménez"],
    "Aragua": ["Maracay", "Girardot", "Zamora", "Mario Briceño Iragorry"],
    "Bolívar": ["Ciudad Bolívar", "Caroní", "Heres"],
}

# ── Vietnam ───────────────────────────────────────────────────────────────────
VIETNAM_PROVINCES: List[str] = [
    "An Giang", "Bà Rịa-Vũng Tàu", "Bắc Giang", "Bắc Kạn", "Bạc Liêu",
    "Bắc Ninh", "Bến Tre", "Bình Dương", "Bình Định", "Bình Phước",
    "Bình Thuận", "Cà Mau", "Cần Thơ", "Cao Bằng", "Đà Nẵng",
    "Đắk Lắk", "Đắk Nông", "Điện Biên", "Đồng Nai", "Đồng Tháp",
    "Gia Lai", "Hà Giang", "Hà Nam", "Hà Nội", "Hà Tĩnh",
    "Hải Dương", "Hải Phòng", "Hậu Giang", "Hòa Bình", "Hồ Chí Minh City",
    "Hưng Yên", "Khánh Hòa", "Kiên Giang", "Kon Tum", "Lai Châu",
    "Lâm Đồng", "Lạng Sơn", "Lào Cai", "Long An", "Nam Định",
    "Nghệ An", "Ninh Bình", "Ninh Thuận", "Phú Thọ", "Phú Yên",
    "Quảng Bình", "Quảng Nam", "Quảng Ngãi", "Quảng Ninh", "Quảng Trị",
    "Sóc Trăng", "Sơn La", "Tây Ninh", "Thái Bình", "Thái Nguyên",
    "Thanh Hóa", "Thừa Thiên Huế", "Tiền Giang", "Trà Vinh", "Tuyên Quang",
    "Vĩnh Long", "Vĩnh Phúc", "Yên Bái",
]
VIETNAM_DISTRICTS: Dict[str, List[str]] = {
    "Hà Nội": ["Ba Đình", "Hoàn Kiếm", "Đống Đa", "Hai Bà Trưng", "Cầu Giấy"],
    "Hồ Chí Minh City": ["District 1", "District 3", "Bình Thạnh", "Gò Vấp", "Phú Nhuận"],
    "Đà Nẵng": ["Hải Châu", "Thanh Khê", "Sơn Trà", "Ngũ Hành Sơn"],
    "Hải Phòng": ["Hồng Bàng", "Ngô Quyền", "Lê Chân", "Kiến An"],
    "Cần Thơ": ["Ninh Kiều", "Bình Thủy", "Cái Răng", "Ô Môn"],
    "Bình Dương": ["Thủ Dầu Một", "Thuận An", "Dĩ An", "Bến Cát"],
    "Đồng Nai": ["Biên Hòa", "Long Khánh", "Nhơn Trạch"],
}

# ── Yemen ─────────────────────────────────────────────────────────────────────
YEMEN_GOVERNORATES: List[str] = [
    "Abyan", "Aden", "Al Bayda", "Al Hudaydah", "Al Jawf",
    "Al Mahrah", "Al Mahwit", "Amran", "Dhamar", "Hadhramaut",
    "Hajjah", "Ibb", "Lahij", "Ma'rib", "Raymah",
    "Sa'dah", "Sana'a", "Socotra", "Shabwah", "Taizz",
]
YEMEN_DISTRICTS: Dict[str, List[str]] = {
    "Sana'a": ["Sana'a City", "Bani Matar", "Bani Hushaish", "Hamdan"],
    "Aden": ["Aden City", "Crater", "Khormaksar", "Al Mualla"],
    "Taizz": ["Taizz City", "Al Mudhaffar", "Al Qahirah"],
    "Hadhramaut": ["Mukalla", "Say'un", "Shibam"],
    "Al Hudaydah": ["Hudaydah City", "Zabid", "Bayt al-Faqih"],
    "Ibb": ["Ibb City", "Dhamar City", "Yarim"],
}

# ──────────────────────────────────────────────────────────────────────────────
# AFRICA_LOCATION_SEED — unchanged from original
# ──────────────────────────────────────────────────────────────────────────────
AFRICA_LOCATION_SEED: Dict[str, "CountryLocationConfig"] = {
    "DZ": CountryLocationConfig("Province", "District", ["Algiers", "Oran", "Constantine"]),
    "AO": CountryLocationConfig("Province", "Municipality", ["Luanda", "Benguela", "Huambo"]),
    "BJ": CountryLocationConfig("Department", "Commune", ["Littoral", "Atlantique", "Borgou"]),
    "BW": CountryLocationConfig("District", "Sub-District", ["Central", "Kweneng", "South-East"]),
    "BF": CountryLocationConfig("Region", "Province", ["Centre", "Hauts-Bassins", "Boucle du Mouhoun"]),
    "BI": CountryLocationConfig("Province", "Commune", ["Bujumbura Mairie", "Gitega", "Ngozi"]),
    "CV": CountryLocationConfig("Municipality", "Parish", ["Praia", "Mindelo", "Santa Catarina"]),
    "CM": CountryLocationConfig("Region", "Division", ["Centre", "Littoral", "Northwest"]),
    "CF": CountryLocationConfig("Prefecture", "Sub-Prefecture", ["Bangui", "Ombella-M'Poko", "Lobaye"]),
    "TD": CountryLocationConfig("Region", "Department", ["N'Djamena", "Logone Occidental", "Moyen-Chari"]),
    "KM": CountryLocationConfig("Island", "Commune", ["Grande Comore", "Anjouan", "Mohéli"]),
    "CG": CountryLocationConfig("Department", "District", ["Brazzaville", "Pointe-Noire", "Niari"]),
    "CD": CountryLocationConfig("Province", "Territory", ["Kinshasa", "Katanga", "North Kivu"]),
    "CI": CountryLocationConfig("Region", "Department", ["Abidjan", "Yamoussoukro", "Bas-Sassandra"]),
    "DJ": CountryLocationConfig("Region", "District", ["Djibouti", "Ali Sabieh", "Tadjourah"]),
    "EG": CountryLocationConfig("Governorate", "District", ["Cairo", "Alexandria", "Giza"]),
    "GQ": CountryLocationConfig("Province", "District", ["Litoral", "Kie-Ntem", "Bioko Norte"]),
    "ER": CountryLocationConfig("Region", "Sub-Region", ["Maekel", "Debub", "Anseba"]),
    "SZ": CountryLocationConfig("Region", "Inkhundla", ["Hhohho", "Manzini", "Lubombo"]),
    "ET": CountryLocationConfig("Region", "Zone", ["Addis Ababa", "Oromia", "Amhara"]),
    "GA": CountryLocationConfig("Province", "Department", ["Estuaire", "Haut-Ogooué", "Woleu-Ntem"]),
    "GM": CountryLocationConfig("Division", "District", ["Banjul", "Kanifing", "West Coast"]),
    "GN": CountryLocationConfig("Region", "Prefecture", ["Conakry", "Boké", "Kankan"]),
    "GW": CountryLocationConfig("Region", "Sector", ["Bissau", "Bafatá", "Gabú"]),
    "LS": CountryLocationConfig("District", "Community Council", ["Maseru", "Berea", "Leribe"]),
    "LR": CountryLocationConfig("County", "District", ["Montserrado", "Bong", "Nimba"]),
    "LY": CountryLocationConfig("District", "Municipality", ["Tripoli", "Benghazi", "Misrata"]),
    "MG": CountryLocationConfig("Region", "District", ["Analamanga", "Atsinanana", "Boeny"]),
    "MW": CountryLocationConfig("Region", "District", ["Central", "Northern", "Southern"]),
    "ML": CountryLocationConfig("Region", "Cercle", ["Bamako", "Sikasso", "Koulikoro"]),
    "MR": CountryLocationConfig("Region", "Department", ["Nouakchott", "Dakhlet Nouadhibou", "Trarza"]),
    "MU": CountryLocationConfig("District", "Village Council", ["Port Louis", "Plaines Wilhems", "Pamplemousses"]),
    "MA": CountryLocationConfig("Region", "Province", ["Casablanca-Settat", "Rabat-Salé-Kénitra", "Marrakech-Safi"]),
    "MZ": CountryLocationConfig("Province", "District", ["Maputo", "Sofala", "Nampula"]),
    "NA": CountryLocationConfig("Region", "Constituency", ["Khomas", "Erongo", "Oshana"]),
    "NE": CountryLocationConfig("Region", "Department", ["Niamey", "Zinder", "Maradi"]),
    "RW": CountryLocationConfig("Province", "District", ["Kigali", "Northern", "Southern"]),
    "ST": CountryLocationConfig("District", "Parish", ["Água Grande", "Mé-Zóchi", "Cantagalo"]),
    "SN": CountryLocationConfig("Region", "Department", ["Dakar", "Thiès", "Saint-Louis"]),
    "SC": CountryLocationConfig("District", "Sub-District", ["Victoria", "Anse Boileau", "Beau Vallon"]),
    "SL": CountryLocationConfig("Province", "District", ["Western Area", "Northern", "Southern"]),
    "SO": CountryLocationConfig("Region", "District", ["Banaadir", "Puntland", "Somaliland"]),
    "SS": CountryLocationConfig("State", "County", ["Central Equatoria", "Jonglei", "Upper Nile"]),
    "SD": CountryLocationConfig("State", "Locality", ["Khartoum", "Kassala", "Darfur"]),
    "TZ": CountryLocationConfig("Region", "District", ["Dar es Salaam", "Arusha", "Mwanza"]),
    "TG": CountryLocationConfig("Region", "Prefecture", ["Maritime", "Plateaux", "Centrale"]),
    "TN": CountryLocationConfig("Governorate", "Delegation", ["Tunis", "Sfax", "Sousse"]),
    "UG": CountryLocationConfig("Region", "District", ["Central", "Eastern", "Northern"]),
    "ZM": CountryLocationConfig("Province", "District", ["Lusaka", "Copperbelt", "Southern"]),
    "ZW": CountryLocationConfig("Province", "District", ["Harare", "Bulawayo", "Matabeleland North"]),
}


# ──────────────────────────────────────────────────────────────────────────────
# LOCATION_CONFIG — complete, covering every country in COUNTRY_NAMES
# ──────────────────────────────────────────────────────────────────────────────


# ── Canonical country catalogue ───────────────────────────────────────────────
COUNTRY_NAMES: Dict[str, str] = {
    'AD': 'Andorra',
    'AE': 'United Arab Emirates',
    'AF': 'Afghanistan',
    'AG': 'Antigua and Barbuda',
    'AI': 'Anguilla',
    'AL': 'Albania',
    'AM': 'Armenia',
    'AO': 'Angola',
    'AQ': 'Antarctica',
    'AR': 'Argentina',
    'AS': 'American Samoa',
    'AT': 'Austria',
    'AU': 'Australia',
    'AW': 'Aruba',
    'AX': 'Åland Islands',
    'AZ': 'Azerbaijan',
    'BA': 'Bosnia and Herzegovina',
    'BB': 'Barbados',
    'BD': 'Bangladesh',
    'BE': 'Belgium',
    'BF': 'Burkina Faso',
    'BG': 'Bulgaria',
    'BH': 'Bahrain',
    'BI': 'Burundi',
    'BJ': 'Benin',
    'BL': 'Saint Barthélemy',
    'BM': 'Bermuda',
    'BN': 'Brunei',
    'BO': 'Bolivia',
    'BQ': 'Bonaire, Sint Eustatius and Saba',
    'BR': 'Brazil',
    'BS': 'Bahamas',
    'BT': 'Bhutan',
    'BV': 'Bouvet Island',
    'BW': 'Botswana',
    'BY': 'Belarus',
    'BZ': 'Belize',
    'CA': 'Canada',
    'CC': 'Cocos (Keeling) Islands',
    'CD': 'Democratic Republic of the Congo',
    'CF': 'Central African Republic',
    'CG': 'Congo',
    'CH': 'Switzerland',
    'CI': "Côte d'Ivoire",
    'CK': 'Cook Islands',
    'CL': 'Chile',
    'CM': 'Cameroon',
    'CN': 'China',
    'CO': 'Colombia',
    'CR': 'Costa Rica',
    'CU': 'Cuba',
    'CV': 'Cabo Verde',
    'CW': 'Curaçao',
    'CX': 'Christmas Island',
    'CY': 'Cyprus',
    'CZ': 'Czech Republic',
    'DE': 'Germany',
    'DJ': 'Djibouti',
    'DK': 'Denmark',
    'DM': 'Dominica',
    'DO': 'Dominican Republic',
    'DZ': 'Algeria',
    'EC': 'Ecuador',
    'EE': 'Estonia',
    'EG': 'Egypt',
    'EH': 'Western Sahara',
    'ER': 'Eritrea',
    'ES': 'Spain',
    'ET': 'Ethiopia',
    'FI': 'Finland',
    'FJ': 'Fiji',
    'FK': 'Falkland Islands (Malvinas)',
    'FM': 'Micronesia',
    'FO': 'Faroe Islands',
    'FR': 'France',
    'GA': 'Gabon',
    'GB': 'United Kingdom',
    'GD': 'Grenada',
    'GE': 'Georgia',
    'GF': 'French Guiana',
    'GG': 'Guernsey',
    'GH': 'Ghana',
    'GI': 'Gibraltar',
    'GL': 'Greenland',
    'GM': 'Gambia',
    'GN': 'Guinea',
    'GP': 'Guadeloupe',
    'GQ': 'Equatorial Guinea',
    'GR': 'Greece',
    'GS': 'South Georgia and the South Sandwich Islands',
    'GT': 'Guatemala',
    'GU': 'Guam',
    'GW': 'Guinea-Bissau',
    'GY': 'Guyana',
    'HK': 'Hong Kong',
    'HM': 'Heard Island and McDonald Islands',
    'HN': 'Honduras',
    'HR': 'Croatia',
    'HT': 'Haiti',
    'HU': 'Hungary',
    'ID': 'Indonesia',
    'IE': 'Ireland',
    'IL': 'Israel',
    'IM': 'Isle of Man',
    'IN': 'India',
    'IO': 'British Indian Ocean Territory',
    'IQ': 'Iraq',
    'IR': 'Iran',
    'IS': 'Iceland',
    'IT': 'Italy',
    'JE': 'Jersey',
    'JM': 'Jamaica',
    'JO': 'Jordan',
    'JP': 'Japan',
    'KE': 'Kenya',
    'KG': 'Kyrgyzstan',
    'KH': 'Cambodia',
    'KI': 'Kiribati',
    'KM': 'Comoros',
    'KN': 'Saint Kitts and Nevis',
    'KP': 'North Korea',
    'KR': 'South Korea',
    'KW': 'Kuwait',
    'KY': 'Cayman Islands',
    'KZ': 'Kazakhstan',
    'LA': 'Laos',
    'LB': 'Lebanon',
    'LC': 'Saint Lucia',
    'LI': 'Liechtenstein',
    'LK': 'Sri Lanka',
    'LR': 'Liberia',
    'LS': 'Lesotho',
    'LT': 'Lithuania',
    'LU': 'Luxembourg',
    'LV': 'Latvia',
    'LY': 'Libya',
    'MA': 'Morocco',
    'MC': 'Monaco',
    'MD': 'Moldova',
    'ME': 'Montenegro',
    'MF': 'Saint Martin (French part)',
    'MG': 'Madagascar',
    'MH': 'Marshall Islands',
    'MK': 'North Macedonia',
    'ML': 'Mali',
    'MM': 'Myanmar',
    'MN': 'Mongolia',
    'MO': 'Macao',
    'MP': 'Northern Mariana Islands',
    'MQ': 'Martinique',
    'MR': 'Mauritania',
    'MS': 'Montserrat',
    'MT': 'Malta',
    'MU': 'Mauritius',
    'MV': 'Maldives',
    'MW': 'Malawi',
    'MX': 'Mexico',
    'MY': 'Malaysia',
    'MZ': 'Mozambique',
    'NA': 'Namibia',
    'NC': 'New Caledonia',
    'NE': 'Niger',
    'NF': 'Norfolk Island',
    'NG': 'Nigeria',
    'NI': 'Nicaragua',
    'NL': 'Netherlands',
    'NO': 'Norway',
    'NP': 'Nepal',
    'NR': 'Nauru',
    'NU': 'Niue',
    'NZ': 'New Zealand',
    'OM': 'Oman',
    'PA': 'Panama',
    'PE': 'Peru',
    'PF': 'French Polynesia',
    'PG': 'Papua New Guinea',
    'PH': 'Philippines',
    'PK': 'Pakistan',
    'PL': 'Poland',
    'PM': 'Saint Pierre and Miquelon',
    'PN': 'Pitcairn',
    'PR': 'Puerto Rico',
    'PS': 'Palestine',
    'PT': 'Portugal',
    'PW': 'Palau',
    'PY': 'Paraguay',
    'QA': 'Qatar',
    'RE': 'Réunion',
    'RO': 'Romania',
    'RS': 'Serbia',
    'RU': 'Russia',
    'RW': 'Rwanda',
    'SA': 'Saudi Arabia',
    'SB': 'Solomon Islands',
    'SC': 'Seychelles',
    'SD': 'Sudan',
    'SE': 'Sweden',
    'SG': 'Singapore',
    'SH': 'Saint Helena, Ascension and Tristan da Cunha',
    'SI': 'Slovenia',
    'SJ': 'Svalbard and Jan Mayen',
    'SK': 'Slovakia',
    'SL': 'Sierra Leone',
    'SM': 'San Marino',
    'SN': 'Senegal',
    'SO': 'Somalia',
    'SR': 'Suriname',
    'SS': 'South Sudan',
    'ST': 'São Tomé and Príncipe',
    'SV': 'El Salvador',
    'SX': 'Sint Maarten (Dutch part)',
    'SY': 'Syria',
    'SZ': 'Eswatini',
    'TC': 'Turks and Caicos Islands',
    'TD': 'Chad',
    'TF': 'French Southern Territories',
    'TG': 'Togo',
    'TH': 'Thailand',
    'TJ': 'Tajikistan',
    'TK': 'Tokelau',
    'TL': 'Timor-Leste',
    'TM': 'Turkmenistan',
    'TN': 'Tunisia',
    'TO': 'Tonga',
    'TR': 'Türkiye',
    'TT': 'Trinidad and Tobago',
    'TV': 'Tuvalu',
    'TW': 'Taiwan',
    'TZ': 'Tanzania',
    'UA': 'Ukraine',
    'UG': 'Uganda',
    'UM': 'United States Minor Outlying Islands',
    'US': 'United States',
    'UY': 'Uruguay',
    'UZ': 'Uzbekistan',
    'VA': 'Vatican City',
    'VC': 'Saint Vincent and the Grenadines',
    'VE': 'Venezuela',
    'VG': 'Virgin Islands, British',
    'VI': 'Virgin Islands, U.S.',
    'VN': 'Vietnam',
    'VU': 'Vanuatu',
    'WF': 'Wallis and Futuna',
    'WS': 'Samoa',
    'XK': 'Kosovo',
    'YE': 'Yemen',
    'YT': 'Mayotte',
    'ZA': 'South Africa',
    'ZM': 'Zambia',
    'ZW': 'Zimbabwe',
}

# ── Canonical country -> region -> subregion configuration ───────────────────
LOCATION_CONFIG: Dict[str, CountryLocationConfig] = {
    'AD': CountryLocationConfig(
        region_label='Parish',
        subregion_label='Commune',
        regions=['Andorra la Vella', 'Canillo', 'Encamp', 'Escaldes-Engordany', 'La Massana', 'Ordino', 'Sant Julià de Lòria'],
        subregions={'Andorra la Vella': ['Andorra la Vella City'], 'Escaldes-Engordany': ['Escaldes', 'Engordany'], 'Encamp': ['Encamp Village', 'Canillo Village'], 'La Massana': ['La Massana Village', 'Ordino Village'], 'Sant Julià de Lòria': ['Sant Julià de Lòria Village']},
    ),
    'AE': CountryLocationConfig(
        region_label='Emirate',
        subregion_label='City',
        regions=['Abu Dhabi', 'Dubai', 'Sharjah', 'Ajman', 'Umm Al Quwain', 'Ras Al Khaimah', 'Fujairah', 'Abū Z̧aby', 'Dubayy', 'Al Fujayrah', 'Ra’s al Khaymah', 'Ash Shāriqah', 'Umm al Qaywayn'],
        subregions={},
    ),
    'AF': CountryLocationConfig(
        region_label='Province',
        subregion_label='District',
        regions=['Kabul', 'Herat', 'Kandahar', 'Balkh', 'Nangarhar', 'Kunduz', 'Ghazni', 'Badakhshan', 'Takhar', 'Baghlan', 'Wardak', 'Logar', 'Paktia', 'Khost', 'Laghman', 'Kunar', 'Nuristan', 'Kapisa', 'Parwan', 'Bamyan', 'Daikundi', 'Ghor', 'Farah', 'Nimroz', 'Helmand', 'Zabul', 'Uruzgan', 'Paktika', 'Samangan', 'Jawzjan', 'Sar-e Pol', 'Faryab', 'Badghis', 'Sari Pul', 'Daykundi', 'Jowzjān', 'Panjshayr', 'Paktiyā', 'Sar-e Pul'],
        subregions={'Kabul': ['Kabul City', 'Bagram', 'Mir Bacha Kot', 'Deh Sabz', 'Khaki Jabbar'], 'Herat': ['Herat City', 'Guzara', 'Injil', 'Pashtun Zarghun', 'Adraskan'], 'Kandahar': ['Kandahar City', 'Arghandab', 'Spin Boldak', 'Panjwai', 'Daman'], 'Balkh': ['Mazar-i-Sharif', 'Dehdadi', 'Nahr-e Shahi', 'Dawlatabad', 'Khulm'], 'Nangarhar': ['Jalalabad', 'Behsud', 'Rodat', 'Kama', 'Surkhrod']},
    ),
    'AG': CountryLocationConfig(
        region_label='Parish',
        subregion_label='Village',
        regions=['Saint George', 'Saint John', 'Saint Mary', 'Saint Paul', 'Saint Peter', 'Saint Philip', 'Barbuda', 'Redonda'],
        subregions={'Saint John': ["Saint John's City", 'Falmouth', 'All Saints'], 'Saint George': ['Liberta', 'Swetes', 'Freetown'], 'Saint Mary': ['Old Road', 'Bolans', 'Jennings'], 'Barbuda': ['Codrington']},
    ),
    'AI': CountryLocationConfig(
        region_label='Territory',
        subregion_label='Locality',
        regions=['Anguilla'],
        subregions={},
    ),
    'AL': CountryLocationConfig(
        region_label='County',
        subregion_label='Municipality',
        regions=['Berat', 'Dibër', 'Durrës', 'Elbasan', 'Fier', 'Gjirokastër', 'Korçë', 'Kukës', 'Lezhë', 'Shkodër', 'Tiranë', 'Vlorë'],
        subregions={'Tiranë': ['Tirana', 'Kamëz', 'Kashar', 'Paskuqan', 'Vora'], 'Durrës': ['Durrës City', 'Krujë', 'Shijak', 'Kavajë'], 'Vlorë': ['Vlorë City', 'Sarandë', 'Himarë', 'Selenicë'], 'Shkodër': ['Shkodër City', 'Lezhë City', 'Laç'], 'Fier': ['Fier City', 'Lushnjë', 'Berat City', 'Kuçovë']},
    ),
    'AM': CountryLocationConfig(
        region_label='Province',
        subregion_label='Community',
        regions=['Aragatsotn', 'Ararat', 'Armavir', 'Gegharkunik', 'Kotayk', 'Lori', 'Shirak', 'Syunik', 'Tavush', 'Vayots Dzor', 'Yerevan', 'Aragac̣otn', 'Erevan', "Geġark'unik'", 'Širak', 'Tavuš', 'Vayoć Jor'],
        subregions={'Yerevan': ['Yerevan City', 'Abovyan', 'Charentsavan'], 'Kotayk': ['Hrazdan', 'Abovyan', 'Kotayk', 'Charentsavan'], 'Ararat': ['Artashat', 'Masis', 'Vedi'], 'Lori': ['Vanadzor', 'Alaverdi', 'Stepanavan'], 'Shirak': ['Gyumri', 'Artik']},
    ),
    'AO': CountryLocationConfig(
        region_label='Province',
        subregion_label='Municipality',
        regions=['Luanda', 'Benguela', 'Huambo', 'Bengo', 'Bié', 'Cabinda', 'Cuando Cubango', 'Cunene', 'Cuanza-Norte', 'Cuanza-Sul', 'Huíla', 'Lunda-Norte', 'Lunda-Sul', 'Malange', 'Moxico', 'Namibe', 'Uíge', 'Zaire'],
        subregions={},
    ),
    'AQ': CountryLocationConfig(
        region_label='Territory',
        subregion_label='Locality',
        regions=['Antarctica'],
        subregions={},
    ),
    'AR': CountryLocationConfig(
        region_label='Province',
        subregion_label='Department',
        regions=['Buenos Aires', 'Catamarca', 'Chaco', 'Chubut', 'Córdoba', 'Corrientes', 'Entre Ríos', 'Formosa', 'Jujuy', 'La Pampa', 'La Rioja', 'Mendoza', 'Misiones', 'Neuquén', 'Río Negro', 'Salta', 'San Juan', 'San Luis', 'Santa Cruz', 'Santa Fe', 'Santiago del Estero', 'Tierra del Fuego', 'Tucumán', 'Ciudad Autónoma de Buenos Aires'],
        subregions={'Buenos Aires': ['La Plata', 'Mar del Plata', 'Quilmes', 'Lomas de Zamora', 'Lanús'], 'Córdoba': ['Córdoba Capital', 'Villa María', 'Río Cuarto', 'San Francisco'], 'Santa Fe': ['Rosario', 'Santa Fe City', 'Rafaela', 'Venado Tuerto'], 'Mendoza': ['Mendoza Capital', 'San Rafael', 'Luján de Cuyo', 'Godoy Cruz'], 'Tucumán': ['San Miguel de Tucumán', 'Concepción', 'Tafí Viejo']},
    ),
    'AS': CountryLocationConfig(
        region_label='Territory',
        subregion_label='Locality',
        regions=['American Samoa'],
        subregions={},
    ),
    'AT': CountryLocationConfig(
        region_label='State',
        subregion_label='District',
        regions=['Burgenland', 'Carinthia', 'Lower Austria', 'Upper Austria', 'Salzburg', 'Styria', 'Tyrol', 'Vorarlberg', 'Vienna', 'Kärnten', 'Niederösterreich', 'Oberösterreich', 'Steiermark', 'Tirol', 'Wien'],
        subregions={'Vienna': ['Vienna City'], 'Lower Austria': ['St. Pölten', 'Krems', 'Baden', 'Mödling', 'Wiener Neustadt'], 'Upper Austria': ['Linz', 'Wels', 'Steyr', 'Traun', 'Leonding'], 'Styria': ['Graz', 'Leoben', 'Klagenfurt', 'Villach'], 'Salzburg': ['Salzburg City', 'Hallein', 'Salzburg-Umgebung'], 'Tyrol': ['Innsbruck', 'Kufstein', 'Schwaz', 'Kitzbühel'], 'Carinthia': ['Klagenfurt', 'Villach', 'Wolfsberg'], 'Vorarlberg': ['Bregenz', 'Dornbirn', 'Feldkirch', 'Bludenz'], 'Burgenland': ['Eisenstadt', 'Neusiedl am See', 'Mattersburg']},
    ),
    'AU': CountryLocationConfig(
        region_label='State',
        subregion_label='Local Government Area',
        regions=['New South Wales', 'Victoria', 'Queensland', 'Western Australia', 'South Australia', 'Tasmania', 'Australian Capital Territory', 'Northern Territory'],
        subregions={'New South Wales': ['Sydney', 'Newcastle', 'Wollongong', 'Central Coast', 'Blue Mountains'], 'Victoria': ['Melbourne', 'Geelong', 'Ballarat', 'Bendigo', 'Shepparton'], 'Queensland': ['Brisbane', 'Gold Coast', 'Sunshine Coast', 'Townsville', 'Cairns'], 'Western Australia': ['Perth', 'Fremantle', 'Joondalup', 'Stirling', 'Mandurah'], 'South Australia': ['Adelaide', 'Mount Gambier', 'Whyalla', 'Murray Bridge'], 'Tasmania': ['Hobart', 'Launceston', 'Devonport', 'Burnie'], 'Australian Capital Territory': ['Canberra', 'Tuggeranong', 'Belconnen', 'Woden'], 'Northern Territory': ['Darwin', 'Alice Springs', 'Palmerston', 'Katherine']},
    ),
    'AW': CountryLocationConfig(
        region_label='Territory',
        subregion_label='Locality',
        regions=['Aruba'],
        subregions={},
    ),
    'AX': CountryLocationConfig(
        region_label='Territory',
        subregion_label='Locality',
        regions=['Åland Islands'],
        subregions={},
    ),
    'AZ': CountryLocationConfig(
        region_label='District',
        subregion_label='Municipality',
        regions=['Absheron', 'Agdam', 'Agdash', 'Aghjabadi', 'Agstafa', 'Agsu', 'Astara', 'Balakan', 'Barda', 'Beylagan', 'Bilasuvar', 'Dashkasan', 'Fizuli', 'Gadabay', 'Goranboy', 'Goychay', 'Goygol', 'Hajigabul', 'Imishli', 'Ismailli', 'Jabrayil', 'Jalilabad', 'Kalbajar', 'Lachin', 'Lerik', 'Masally', 'Mingachevir', 'Nakhchivan', 'Neftchala', 'Oguz', 'Qax', 'Qazakh', 'Quba', 'Qubadli', 'Qusar', 'Saatly', 'Sabirabad', 'Salyan', 'Shamakhi', 'Shamkir', 'Shirvan', 'Shusha', 'Siazan', 'Sumgayit', 'Tartar', 'Tovuz', 'Ujar', 'Khachmaz', 'Khankendi', 'Khizi', 'Baku', 'Ganja', 'Lankaran', 'Shaki', 'Zaqatala', 'Zardab', 'Abşeron', 'Ağcabədi', 'Ağdaş', 'Bakı', 'Balakən', 'Bərdə', 'Beyləqan', 'Biləsuvar', 'Cəbrayıl', 'Cəlilabad', 'Daşkəsən', 'Füzuli', 'Gəncə', 'Gədəbəy', 'Göyçay', 'Hacıqabul', 'İmişli', 'İsmayıllı', 'Kəlbəcər', 'Kürdəmir', 'Lənkəran', 'Laçın', 'Masallı', 'Mingəçevir', 'Naftalan', 'Neftçala', 'Naxçıvan', 'Qəbələ', 'Qazax', 'Qubadlı', 'Qobustan', 'Şəki', 'Saatlı', 'Şabran', 'Siyəzən', 'Şəmkir', 'Sumqayıt', 'Şamaxı', 'Samux', 'Şirvan', 'Şuşa', 'Tərtər', 'Ucar', 'Xankəndi', 'Xaçmaz', 'Xocalı', 'Xızı', 'Xocavənd', 'Yardımlı', 'Yevlax', 'Zəngilan', 'Zərdab'],
        subregions={'Baku': ['Baku City', 'Sabunchu', 'Surakhani', 'Binagadi', 'Narimanov'], 'Ganja': ['Ganja City', 'Khanlar'], 'Sumgayit': ['Sumgayit City'], 'Lankaran': ['Lankaran City', 'Astara City'], 'Shaki': ['Shaki City', 'Oguz'], 'Nakhchivan': ['Nakhchivan City', 'Ordubad', 'Julfa']},
    ),
    'BA': CountryLocationConfig(
        region_label='Entity',
        subregion_label='Canton',
        regions=['Federation of Bosnia and Herzegovina', 'Republika Srpska', 'Brčko District', 'Federacija Bosne i Hercegovine', 'Brčko distrikt'],
        subregions={'Federation of Bosnia and Herzegovina': ['Una-Sana Canton', 'Posavina Canton', 'Tuzla Canton', 'Zenica-Doboj Canton', 'Bosnian Podrinje Canton', 'Central Bosnia Canton', 'Herzegovina-Neretva Canton', 'West Herzegovina Canton', 'Sarajevo Canton', 'Canton 10'], 'Republika Srpska': ['Banja Luka', 'Bijeljina', 'Doboj', 'Trebinje', 'Zvornik'], 'Brčko District': ['Brčko']},
    ),
    'BB': CountryLocationConfig(
        region_label='Parish',
        subregion_label='District',
        regions=['Christ Church', 'Saint Andrew', 'Saint George', 'Saint James', 'Saint John', 'Saint Joseph', 'Saint Lucy', 'Saint Michael', 'Saint Peter', 'Saint Philip', 'Saint Thomas'],
        subregions={'Saint Michael': ['Bridgetown', 'Belleville', 'Fontabelle'], 'Christ Church': ['Oistins', 'Worthing', 'Hastings', 'Maxwell'], 'Saint James': ['Holetown', 'Speightstown'], 'Saint Philip': ['Six Cross Roads', 'Crane'], 'Saint Peter': ['Speightstown', 'Mullins']},
    ),
    'BD': CountryLocationConfig(
        region_label='Division',
        subregion_label='District',
        regions=['Barisal', 'Chittagong', 'Dhaka', 'Khulna', 'Mymensingh', 'Rajshahi', 'Rangpur', 'Sylhet', 'Barishal', 'Chattogram'],
        subregions={'Dhaka': ['Dhaka', 'Gazipur', 'Narayanganj', 'Manikganj', 'Munshiganj', 'Narsingdi'], 'Chittagong': ['Chittagong', "Cox's Bazar", 'Comilla', 'Feni', 'Noakhali', 'Chandpur'], 'Rajshahi': ['Rajshahi', 'Bogura', 'Pabna', 'Naogaon', 'Natore', 'Sirajganj', 'Chapainawabganj'], 'Khulna': ['Khulna', 'Jessore', 'Satkhira', 'Bagerhat', 'Chuadanga', 'Kushtia', 'Magura'], 'Sylhet': ['Sylhet', 'Moulvibazar', 'Habiganj', 'Sunamganj'], 'Barisal': ['Barisal', 'Bhola', 'Patuakhali', 'Pirojpur', 'Barguna', 'Jhalokati'], 'Mymensingh': ['Mymensingh', 'Netrokona', 'Sherpur', 'Jamalpur'], 'Rangpur': ['Rangpur', 'Dinajpur', 'Nilphamari', 'Gaibandha', 'Kurigram', 'Lalmonirhat', 'Thakurgaon', 'Panchagarh']},
    ),
    'BE': CountryLocationConfig(
        region_label='Region',
        subregion_label='Province',
        regions=['Flanders', 'Wallonia', 'Brussels-Capital', 'Bruxelles-Capitale, Région de', 'Vlaams Gewest', 'wallonne, Région'],
        subregions={},
    ),
    'BF': CountryLocationConfig(
        region_label='Region',
        subregion_label='Province',
        regions=['Centre', 'Hauts-Bassins', 'Boucle du Mouhoun', 'Cascades', 'Centre-Est', 'Centre-Nord', 'Centre-Ouest', 'Centre-Sud', 'Est', 'Nord', 'Plateau-Central', 'Sahel', 'Sud-Ouest'],
        subregions={},
    ),
    'BG': CountryLocationConfig(
        region_label='Province',
        subregion_label='Municipality',
        regions=['Blagoevgrad', 'Burgas', 'Dobrich', 'Gabrovo', 'Haskovo', 'Kardzhali', 'Kyustendil', 'Lovech', 'Montana', 'Pazardzhik', 'Pernik', 'Pleven', 'Plovdiv', 'Razgrad', 'Ruse', 'Shumen', 'Silistra', 'Sliven', 'Smolyan', 'Sofia City', 'Sofia Province', 'Stara Zagora', 'Targovishte', 'Varna', 'Veliko Tarnovo', 'Vidin', 'Vratsa', 'Yambol', 'Sofia (stolitsa)', 'Sofia'],
        subregions={'Sofia City': ['Sofia', 'Bankya', 'Novi Iskar', 'Pancharevo'], 'Plovdiv': ['Plovdiv City', 'Asenovgrad', 'Karlovo', 'Rakovsku'], 'Varna': ['Varna City', 'Devnya', 'Aksakovo', 'Beloslav'], 'Burgas': ['Burgas City', 'Sozopol', 'Nessebar', 'Pomorie'], 'Ruse': ['Ruse City', 'Byala', 'Vetovo'], 'Stara Zagora': ['Stara Zagora City', 'Kazanlak', 'Chirpan']},
    ),
    'BH': CountryLocationConfig(
        region_label='Governorate',
        subregion_label='Municipality',
        regions=['Capital', 'Muharraq', 'Northern', 'Southern', 'Al ‘Āşimah', 'Al Janūbīyah', 'Al Muḩarraq', 'Ash Shamālīyah'],
        subregions={'Capital': ['Manama', 'Juffair', 'Adliya', 'Seef', 'Gudaibiya'], 'Muharraq': ['Muharraq City', 'Hidd', 'Arad', 'Busaiteen'], 'Northern': ['Manamah', 'Sitra', 'Budaiya', 'Barbar', 'Hamad Town'], 'Southern': ['Riffa', 'Isa Town', 'Zallaq', 'Awali']},
    ),
    'BI': CountryLocationConfig(
        region_label='Province',
        subregion_label='Commune',
        regions=['Bujumbura Mairie', 'Gitega', 'Ngozi', 'Bubanza', 'Bujumbura Rural', 'Bururi', 'Cankuzo', 'Cibitoke', 'Kirundo', 'Karuzi', 'Kayanza', 'Makamba', 'Muramvya', 'Mwaro', 'Muyinga', 'Rumonge', 'Rutana', 'Ruyigi'],
        subregions={},
    ),
    'BJ': CountryLocationConfig(
        region_label='Department',
        subregion_label='Commune',
        regions=['Littoral', 'Atlantique', 'Borgou', 'Atacora', 'Alibori', 'Collines', 'Donga', 'Couffo', 'Mono', 'Ouémé', 'Plateau', 'Zou'],
        subregions={},
    ),
    'BL': CountryLocationConfig(
        region_label='Territory',
        subregion_label='Locality',
        regions=['Saint Barthélemy'],
        subregions={},
    ),
    'BM': CountryLocationConfig(
        region_label='Territory',
        subregion_label='Locality',
        regions=['Bermuda'],
        subregions={},
    ),
    'BN': CountryLocationConfig(
        region_label='District',
        subregion_label='Mukim',
        regions=['Belait', 'Brunei-Muara', 'Temburong', 'Tutong'],
        subregions={'Brunei-Muara': ['Bandar Seri Begawan', 'Berakas A', 'Berakas B', 'Kota Batu', 'Gadong'], 'Belait': ['Kuala Belait', 'Seria', 'Labi', 'Sukang'], 'Tutong': ['Tutong Town', 'Telisai', 'Lamit'], 'Temburong': ['Bangar', 'Batu Apoi', 'Amo']},
    ),
    'BO': CountryLocationConfig(
        region_label='Department',
        subregion_label='Municipality',
        regions=['Beni', 'Chuquisaca', 'Cochabamba', 'La Paz', 'Oruro', 'Pando', 'Potosí', 'Santa Cruz', 'Tarija', 'El Beni'],
        subregions={'La Paz': ['La Paz City', 'El Alto', 'Viacha', 'Achacachi', 'Copacabana'], 'Santa Cruz': ['Santa Cruz de la Sierra', 'Montero', 'Warnes', 'Cotoca', 'Porongo'], 'Cochabamba': ['Cochabamba City', 'Sacaba', 'Quillacollo', 'Tiquipaya', 'Colcapirhua'], 'Potosí': ['Potosí City', 'Villazón', 'Uyuni', 'Tupiza'], 'Oruro': ['Oruro City', 'Huanuni', 'Challapata'], 'Chuquisaca': ['Sucre', 'Camargo', 'Monteagudo'], 'Tarija': ['Tarija City', 'Yacuiba', 'Villam'], 'Beni': ['Trinidad', 'Riberalta', 'Guayaramerín'], 'Pando': ['Cobija', 'Porvenir']},
    ),
    'BQ': CountryLocationConfig(
        region_label='Region',
        subregion_label='District',
        regions=['Bonaire', 'Saba', 'Sint Eustatius'],
        subregions={},
    ),
    'BR': CountryLocationConfig(
        region_label='State',
        subregion_label='Municipality',
        regions=['Acre', 'Alagoas', 'Amapá', 'Amazonas', 'Bahia', 'Ceará', 'Distrito Federal', 'Espírito Santo', 'Goiás', 'Maranhão', 'Mato Grosso', 'Mato Grosso do Sul', 'Minas Gerais', 'Pará', 'Paraíba', 'Paraná', 'Pernambuco', 'Piauí', 'Rio de Janeiro', 'Rio Grande do Norte', 'Rio Grande do Sul', 'Rondônia', 'Roraima', 'Santa Catarina', 'São Paulo', 'Sergipe', 'Tocantins'],
        subregions={'São Paulo': ['São Paulo City', 'Guarulhos', 'Campinas', 'Santos', 'São Bernardo do Campo'], 'Rio de Janeiro': ['Rio de Janeiro City', 'Niterói', 'Nova Iguaçu', 'Duque de Caxias'], 'Minas Gerais': ['Belo Horizonte', 'Uberlândia', 'Contagem', 'Juiz de Fora'], 'Bahia': ['Salvador', 'Feira de Santana', 'Vitória da Conquista'], 'Paraná': ['Curitiba', 'Londrina', 'Maringá', 'Ponta Grossa'], 'Rio Grande do Sul': ['Porto Alegre', 'Caxias do Sul', 'Pelotas', 'Canoas'], 'Pernambuco': ['Recife', 'Olinda', 'Caruaru', 'Petrolina'], 'Ceará': ['Fortaleza', 'Caucaia', 'Juazeiro do Norte', 'Maracanaú'], 'Goiás': ['Goiânia', 'Aparecida de Goiânia', 'Anápolis'], 'Amazonas': ['Manaus', 'Parintins', 'Itacoatiara']},
    ),
    'BS': CountryLocationConfig(
        region_label='District',
        subregion_label='Settlement',
        regions=['Acklins', 'Berry Islands', 'Bimini', 'Black Point', 'Cat Island', 'Central Abaco', 'Central Andros', 'Central Eleuthera', 'City of Freeport', 'Crooked Island and Long Cay', 'East Grand Bahama', 'Exuma', 'Grand Cay', 'Harbour Island', 'Hope Town', 'Inagua', 'Long Island', 'Mangrove Cay', 'Mayaguana', "Moore's Island", 'New Providence', 'North Abaco', 'North Andros', 'North Eleuthera', 'Ragged Island', 'Rum Cay', 'San Salvador', 'South Abaco', 'South Andros', 'South Eleuthera', 'Spanish Wells', 'West Grand Bahama'],
        subregions={'New Providence': ['Nassau', 'Carmichael', 'Nassau Village'], 'City of Freeport': ['Freeport', 'Eight Mile Rock', 'West End'], 'Exuma': ['George Town', 'Moss Town'], 'Long Island': ['Clarence Town', "Deadman's Cay"]},
    ),
    'BT': CountryLocationConfig(
        region_label='Dzongkhag',
        subregion_label='Gewog',
        regions=['Bumthang', 'Chukha', 'Dagana', 'Gasa', 'Haa', 'Lhuentse', 'Mongar', 'Paro', 'Pemagatshel', 'Punakha', 'Samdrup Jongkhar', 'Samtse', 'Sarpang', 'Thimphu', 'Trashigang', 'Trashiyangtse', 'Trongsa', 'Tsirang', 'Wangdue Phodrang', 'Zhemgang', 'Chhukha', 'Monggar', 'Pema Gatshel', 'Trashi Yangtse'],
        subregions={'Thimphu': ['Chang', 'Dagala', 'Genyekha', 'Kawang', 'Lingzhi', 'Mewang', 'Naro', 'Toedchen'], 'Paro': ['Doga', 'Doteng', 'Lamgong', 'Lungnyi', 'Naja', 'Tsento', 'Wangchang'], 'Punakha': ['Barp', 'Bayi', 'Chhubu', 'Guma', 'Kamichu', 'Talo', 'Toewang'], 'Chukha': ['Bongo', 'Chapcha', 'Darla', 'Dungna', 'Getana', 'Logchina', 'Phuntsholing'], 'Bumthang': ['Chhoekhor', 'Chumey', 'Tang', 'Ura']},
    ),
    'BV': CountryLocationConfig(
        region_label='Territory',
        subregion_label='Locality',
        regions=['Bouvet Island'],
        subregions={},
    ),
    'BW': CountryLocationConfig(
        region_label='District',
        subregion_label='Sub-District',
        regions=['Central', 'Kweneng', 'South-East', 'Chobe', 'Francistown', 'Gaborone', 'Ghanzi', 'Jwaneng', 'Kgalagadi', 'Kgatleng', 'Lobatse', 'North East', 'North West', 'Southern', 'Selibe Phikwe', 'Sowa Town'],
        subregions={},
    ),
    'BY': CountryLocationConfig(
        region_label='Region',
        subregion_label='District',
        regions=['Brest Region', 'Vitebsk Region', 'Gomel Region', 'Grodno Region', 'Minsk Region', 'Mogilev Region', 'Minsk City', 'Bresckaja voblasć', 'Gorod Minsk', "Gomel'skaja oblast'", "Grodnenskaja oblast'", 'Mahilioŭskaja voblasć', "Minskaja oblast'", 'Viciebskaja voblasć'],
        subregions={'Minsk City': ['Minsk City'], 'Minsk Region': ['Barysaw', 'Zhodzina', 'Salihorsk', 'Maladzyechna', 'Vileika'], 'Brest Region': ['Brest', 'Baranavichy', 'Pinsk', 'Luninets'], 'Grodno Region': ['Grodno', 'Lida', 'Slonim', 'Novogrudok'], 'Vitebsk Region': ['Vitebsk', 'Orsha', 'Polotsk', 'Novopolotsk'], 'Mogilev Region': ['Mogilev', 'Bobruisk', 'Byhau'], 'Gomel Region': ['Gomel', 'Mazyr', 'Zhlobin', 'Svetlahorsk']},
    ),
    'BZ': CountryLocationConfig(
        region_label='District',
        subregion_label='Municipality',
        regions=['Belize', 'Cayo', 'Corozal', 'Orange Walk', 'Stann Creek', 'Toledo'],
        subregions={'Belize': ['Belize City', 'Ladyville', 'Hattieville'], 'Cayo': ['Belmopan', 'San Ignacio', 'Santa Elena', 'Benque Viejo'], 'Corozal': ['Corozal Town', 'Consejo', 'Sarteneja'], 'Orange Walk': ['Orange Walk Town', 'Shipyard', 'San Estevan'], 'Stann Creek': ['Dangriga', 'Placencia', 'Hopkins'], 'Toledo': ['Punta Gorda', 'San Antonio', 'Barranco']},
    ),
    'CA': CountryLocationConfig(
        region_label='Province',
        subregion_label='City',
        regions=['Alberta', 'British Columbia', 'Manitoba', 'New Brunswick', 'Newfoundland and Labrador', 'Northwest Territories', 'Nova Scotia', 'Nunavut', 'Ontario', 'Prince Edward Island', 'Quebec', 'Saskatchewan', 'Yukon'],
        subregions={'Ontario': ['Toronto', 'Ottawa', 'Mississauga', 'Hamilton', 'London'], 'British Columbia': ['Vancouver', 'Victoria', 'Surrey', 'Burnaby'], 'Quebec': ['Montreal', 'Quebec City', 'Laval', 'Gatineau'], 'Alberta': ['Calgary', 'Edmonton', 'Red Deer']},
    ),
    'CC': CountryLocationConfig(
        region_label='Territory',
        subregion_label='Locality',
        regions=['Cocos (Keeling) Islands'],
        subregions={},
    ),
    'CD': CountryLocationConfig(
        region_label='Province',
        subregion_label='Territory',
        regions=['Kinshasa', 'Katanga', 'North Kivu', 'Kongo Central', 'Bas-Uélé', 'Équateur', 'Haut-Katanga', 'Haut-Lomami', 'Haut-Uélé', 'Ituri', 'Kasaï Central', 'Kasaï Oriental', 'Kwango', 'Kwilu', 'Kasaï', 'Lomami', 'Lualaba', 'Maniema', 'Mai-Ndombe', 'Mongala', 'Nord-Kivu', 'Nord-Ubangi', 'Sankuru', 'Sud-Kivu', 'Sud-Ubangi', 'Tanganyika', 'Tshopo', 'Tshuapa'],
        subregions={},
    ),
    'CF': CountryLocationConfig(
        region_label='Prefecture',
        subregion_label='Sub-Prefecture',
        regions=['Bangui', "Ombella-M'Poko", 'Lobaye', 'Ouham', 'Bamingui-Bangoran', 'Basse-Kotto', 'Haute-Kotto', 'Haut-Mbomou', 'Haute-Sangha / Mambéré-Kadéï', 'Gribingui', 'Kémo-Gribingui', 'Mbomou', 'Ombella-Mpoko', 'Nana-Mambéré', 'Ouham-Pendé', 'Sangha', 'Ouaka', 'Vakaga'],
        subregions={},
    ),
    'CG': CountryLocationConfig(
        region_label='Department',
        subregion_label='District',
        regions=['Brazzaville', 'Pointe-Noire', 'Niari', 'Bouenza', 'Pool', 'Sangha', 'Plateaux', 'Cuvette-Ouest', 'Lékoumou', 'Kouilou', 'Likouala', 'Cuvette'],
        subregions={},
    ),
    'CH': CountryLocationConfig(
        region_label='Canton',
        subregion_label='Municipality',
        regions=['Zürich', 'Geneva', 'Bern', 'Aargau', 'Appenzell Innerrhoden', 'Appenzell Ausserrhoden', 'Berne', 'Basel-Landschaft', 'Basel-Stadt', 'Fribourg', 'Genève', 'Glarus', 'Graubünden', 'Jura', 'Luzern', 'Neuchâtel', 'Nidwalden', 'Obwalden', 'Sankt Gallen', 'Schaffhausen', 'Solothurn', 'Schwyz', 'Thurgau', 'Ticino', 'Uri', 'Vaud', 'Valais', 'Zug'],
        subregions={},
    ),
    'CI': CountryLocationConfig(
        region_label='Region',
        subregion_label='Department',
        regions=['Abidjan', 'Yamoussoukro', 'Bas-Sassandra', 'Comoé', 'Denguélé', 'Gôh-Djiboua', 'Lacs', 'Lagunes', 'Montagnes', 'Sassandra-Marahoué', 'Savanes', 'Vallée du Bandama', 'Woroba', 'Zanzan'],
        subregions={},
    ),
    'CK': CountryLocationConfig(
        region_label='Territory',
        subregion_label='Locality',
        regions=['Cook Islands'],
        subregions={},
    ),
    'CL': CountryLocationConfig(
        region_label='Region',
        subregion_label='Commune',
        regions=['Arica and Parinacota', 'Tarapacá', 'Antofagasta', 'Atacama', 'Coquimbo', 'Valparaíso', 'Metropolitan Region of Santiago', "O'Higgins", 'Maule', 'Ñuble', 'Biobío', 'La Araucanía', 'Los Ríos', 'Los Lagos', 'Aysén', 'Magallanes', 'Aisén del General Carlos Ibañez del Campo', 'Arica y Parinacota', "Libertador General Bernardo O'Higgins", 'Región Metropolitana de Santiago'],
        subregions={'Metropolitan Region of Santiago': ['Santiago', 'Providencia', 'Las Condes', 'Maipú', 'La Florida'], 'Valparaíso': ['Valparaíso City', 'Viña del Mar', 'Quilpué', 'Villa Alemana'], 'Biobío': ['Concepción', 'Talcahuano', 'Chillán', 'Los Ángeles'], 'La Araucanía': ['Temuco', 'Padre Las Casas', 'Angol', 'Victoria'], 'Los Lagos': ['Puerto Montt', 'Osorno', 'Castro', 'Ancud'], 'Antofagasta': ['Antofagasta City', 'Calama', 'Tocopilla'], 'Coquimbo': ['La Serena', 'Coquimbo City', 'Ovalle', 'Illapel']},
    ),
    'CM': CountryLocationConfig(
        region_label='Region',
        subregion_label='Division',
        regions=['Centre', 'Littoral', 'Northwest', 'Adamaoua', 'Far North', 'East', 'North', 'North-West', 'West', 'South', 'South-West'],
        subregions={},
    ),
    'CN': CountryLocationConfig(
        region_label='Province',
        subregion_label='Prefecture',
        regions=['Anhui', 'Beijing', 'Chongqing', 'Fujian', 'Gansu', 'Guangdong', 'Guangxi', 'Guizhou', 'Hainan', 'Hebei', 'Heilongjiang', 'Henan', 'Hong Kong', 'Hubei', 'Hunan', 'Inner Mongolia', 'Jiangsu', 'Jiangxi', 'Jilin', 'Liaoning', 'Macau', 'Ningxia', 'Qinghai', 'Shaanxi', 'Shandong', 'Shanghai', 'Shanxi', 'Sichuan', 'Tianjin', 'Tibet', 'Xinjiang', 'Yunnan', 'Zhejiang', 'Anhui Sheng', 'Beijing Shi', 'Chongqing Shi', 'Fujian Sheng', 'Guangdong Sheng', 'Gansu Sheng', 'Guangxi Zhuangzu Zizhiqu', 'Guizhou Sheng', 'Henan Sheng', 'Hubei Sheng', 'Hebei Sheng', 'Hainan Sheng', 'Hong Kong SAR', 'Heilongjiang Sheng', 'Hunan Sheng', 'Jilin Sheng', 'Jiangsu Sheng', 'Jiangxi Sheng', 'Liaoning Sheng', 'Macao SAR', 'Nei Mongol Zizhiqu', 'Ningxia Huizu Zizhiqu', 'Qinghai Sheng', 'Sichuan Sheng', 'Shandong Sheng', 'Shanghai Shi', 'Shaanxi Sheng', 'Shanxi Sheng', 'Tianjin Shi', 'Taiwan Sheng', 'Xinjiang Uygur Zizhiqu', 'Xizang Zizhiqu', 'Yunnan Sheng', 'Zhejiang Sheng'],
        subregions={'Guangdong': ['Guangzhou', 'Shenzhen', 'Foshan', 'Dongguan', 'Zhuhai', 'Shantou'], 'Jiangsu': ['Nanjing', 'Suzhou', 'Wuxi', 'Nantong', 'Changzhou', 'Xuzhou'], 'Shandong': ['Jinan', 'Qingdao', 'Yantai', 'Weifang', 'Linyi', 'Zibo'], 'Zhejiang': ['Hangzhou', 'Ningbo', 'Wenzhou', 'Jinhua', 'Shaoxing', 'Taizhou'], 'Sichuan': ['Chengdu', 'Mianyang', 'Deyang', 'Leshan', 'Nanchong'], 'Henan': ['Zhengzhou', 'Luoyang', 'Kaifeng', 'Nanyang', 'Anyang'], 'Hubei': ['Wuhan', 'Yichang', 'Xiangyang', 'Jingzhou'], 'Hunan': ['Changsha', 'Zhuzhou', 'Xiangtan', 'Hengyang'], 'Beijing': ['Chaoyang', 'Haidian', 'Fengtai', 'Dongcheng', 'Xicheng'], 'Shanghai': ['Pudong', "Jing'an", 'Xuhui', 'Huangpu', 'Yangpu']},
    ),
    'CO': CountryLocationConfig(
        region_label='Department',
        subregion_label='Municipality',
        regions=['Amazonas', 'Antioquia', 'Arauca', 'Atlántico', 'Bolívar', 'Boyacá', 'Caldas', 'Caquetá', 'Casanare', 'Cauca', 'Cesar', 'Chocó', 'Córdoba', 'Cundinamarca', 'Guainía', 'Guaviare', 'Huila', 'La Guajira', 'Magdalena', 'Meta', 'Nariño', 'Norte de Santander', 'Putumayo', 'Quindío', 'Risaralda', 'San Andrés y Providencia', 'Santander', 'Sucre', 'Tolima', 'Valle del Cauca', 'Vaupés', 'Vichada', 'Bogotá D.C.', 'Distrito Capital de Bogotá', 'San Andrés, Providencia y Santa Catalina'],
        subregions={'Bogotá D.C.': ['Bogotá City'], 'Antioquia': ['Medellín', 'Bello', 'Envigado', 'Itagüí', 'Bucaramanga'], 'Valle del Cauca': ['Cali', 'Buenaventura', 'Palmira', 'Buga', 'Tulúa'], 'Cundinamarca': ['Soacha', 'Fusagasugá', 'Facatativá', 'Zipaquirá'], 'Atlántico': ['Barranquilla', 'Soledad', 'Malambo', 'Sabanalarga'], 'Bolívar': ['Cartagena', 'Magangué', 'El Carmen de Bolívar'], 'Santander': ['Bucaramanga', 'Floridablanca', 'Girón', 'Piedecuesta']},
    ),
    'CR': CountryLocationConfig(
        region_label='Province',
        subregion_label='Canton',
        regions=['Alajuela', 'Cartago', 'Guanacaste', 'Heredia', 'Limón', 'Puntarenas', 'San José'],
        subregions={'San José': ['San José City', 'Escazú', 'Desamparados', 'Aserrí', 'Moravia'], 'Alajuela': ['Alajuela City', 'San Ramón', 'Grecia', 'San Carlos', 'Palmares'], 'Cartago': ['Cartago City', 'Paraíso', 'La Unión', 'Turrialba'], 'Heredia': ['Heredia City', 'Barva', 'Santo Domingo', 'Santa Bárbara'], 'Guanacaste': ['Liberia', 'Nicoya', 'Santa Cruz', 'Bagaces'], 'Puntarenas': ['Puntarenas City', 'Quepos', 'Osa', 'Golfito'], 'Limón': ['Limón City', 'Pococí', 'Siquirres', 'Talamanca']},
    ),
    'CU': CountryLocationConfig(
        region_label='Province',
        subregion_label='Municipality',
        regions=['Artemisa', 'Camagüey', 'Ciego de Ávila', 'Cienfuegos', 'Granma', 'Guantánamo', 'Havana', 'Holguín', 'Isla de la Juventud', 'Las Tunas', 'Matanzas', 'Mayabeque', 'Pinar del Río', 'Sancti Spíritus', 'Santiago de Cuba', 'Villa Clara', 'La Habana'],
        subregions={'Havana': ['Havana City', 'Boyeros', 'Playa', 'Plaza de la Revolución', 'Centro Habana'], 'Santiago de Cuba': ['Santiago City', 'Palma Soriano', 'Contramaestre'], 'Holguín': ['Holguín City', 'Moa', 'Banes', 'Gibara'], 'Camagüey': ['Camagüey City', 'Florida', 'Nuevitas', 'Guáimaro'], 'Villa Clara': ['Santa Clara', 'Cienfuegos City', 'Sagua la Grande']},
    ),
    'CV': CountryLocationConfig(
        region_label='Municipality',
        subregion_label='Parish',
        regions=['Praia', 'Mindelo', 'Santa Catarina', 'Ilhas de Barlavento', 'Ilhas de Sotavento'],
        subregions={},
    ),
    'CW': CountryLocationConfig(
        region_label='Territory',
        subregion_label='Locality',
        regions=['Curaçao'],
        subregions={},
    ),
    'CX': CountryLocationConfig(
        region_label='Territory',
        subregion_label='Locality',
        regions=['Christmas Island'],
        subregions={},
    ),
    'CY': CountryLocationConfig(
        region_label='District',
        subregion_label='Municipality',
        regions=['Famagusta', 'Kyrenia', 'Larnaca', 'Limassol', 'Nicosia', 'Paphos', 'Lefkosia', 'Lemesos', 'Larnaka', 'Ammochostos', 'Baf', 'Girne'],
        subregions={'Nicosia': ['Nicosia City', 'Strovolos', 'Lakatamia', 'Aglandjia'], 'Limassol': ['Limassol City', 'Germasogeia', 'Mesa Geitonia'], 'Larnaca': ['Larnaca City', 'Aradippou', 'Livadia'], 'Paphos': ['Paphos City', 'Peyia', 'Chlorakas'], 'Famagusta': ['Paralimni', 'Derynia', 'Sotira'], 'Kyrenia': ['Kyrenia City']},
    ),
    'CZ': CountryLocationConfig(
        region_label='Region',
        subregion_label='District',
        regions=['Central Bohemian Region', 'South Bohemian Region', 'Plzeň Region', 'Karlovy Vary Region', 'Ústí nad Labem Region', 'Liberec Region', 'Hradec Králové Region', 'Pardubice Region', 'Olomouc Region', 'Moravian-Silesian Region', 'South Moravian Region', 'Zlín Region', 'Vysočina Region', 'Prague', 'Praha, Hlavní město', 'Středočeský kraj', 'Jihočeský kraj', 'Plzeňský kraj', 'Karlovarský kraj', 'Ústecký kraj', 'Liberecký kraj', 'Královéhradecký kraj', 'Pardubický kraj', 'Kraj Vysočina', 'Jihomoravský kraj', 'Olomoucký kraj', 'Zlínský kraj', 'Moravskoslezský kraj'],
        subregions={'Prague': ['Prague 1', 'Prague 2', 'Prague 3', 'Prague 4', 'Prague 5', 'Prague 6'], 'South Moravian Region': ['Brno', 'Znojmo', 'Břeclav', 'Hodonín', 'Vyškov'], 'Moravian-Silesian Region': ['Ostrava', 'Opava', 'Frýdek-Místek', 'Karviná'], 'Plzeň Region': ['Plzeň', 'Klatovy', 'Domažlice', 'Tachov'], 'Central Bohemian Region': ['Mladá Boleslav', 'Kladno', 'Příbram', 'Nymburk'], 'Ústí nad Labem Region': ['Ústí nad Labem', 'Most', 'Teplice', 'Chomutov']},
    ),
    'DE': CountryLocationConfig(
        region_label='State',
        subregion_label='District',
        regions=['Bavaria', 'Berlin', 'North Rhine-Westphalia', 'Brandenburg', 'Baden-Württemberg', 'Bayern', 'Bremen', 'Hessen', 'Hamburg', 'Mecklenburg-Vorpommern', 'Niedersachsen', 'Nordrhein-Westfalen', 'Rheinland-Pfalz', 'Schleswig-Holstein', 'Saarland', 'Sachsen', 'Sachsen-Anhalt', 'Thüringen'],
        subregions={},
    ),
    'DJ': CountryLocationConfig(
        region_label='Region',
        subregion_label='District',
        regions=['Djibouti', 'Ali Sabieh', 'Tadjourah', 'Arta', 'Dikhil', 'Obock'],
        subregions={},
    ),
    'DK': CountryLocationConfig(
        region_label='Region',
        subregion_label='Municipality',
        regions=['Capital Region of Denmark', 'Central Denmark Region', 'North Denmark Region', 'Region of Southern Denmark', 'Region Zealand', 'Nordjylland', 'Midtjylland', 'Syddanmark', 'Hovedstaden', 'Sjælland'],
        subregions={'Capital Region of Denmark': ['Copenhagen', 'Frederiksberg', 'Gentofte', 'Gladsaxe', 'Ballerup'], 'Central Denmark Region': ['Aarhus', 'Silkeborg', 'Randers', 'Horsens', 'Viborg'], 'Region of Southern Denmark': ['Odense', 'Esbjerg', 'Vejle', 'Kolding', 'Sønderborg'], 'North Denmark Region': ['Aalborg', 'Hjørring', 'Frederikshavn', 'Thisted'], 'Region Zealand': ['Roskilde', 'Slagelse', 'Køge', 'Næstved', 'Holbæk']},
    ),
    'DM': CountryLocationConfig(
        region_label='Parish',
        subregion_label='Village',
        regions=['Saint Andrew', 'Saint David', 'Saint George', 'Saint John', 'Saint Joseph', 'Saint Luke', 'Saint Mark', 'Saint Patrick', 'Saint Paul', 'Saint Peter'],
        subregions={'Saint George': ['Roseau', 'Canefield'], 'Saint Andrew': ['Marigot', 'Wesley', 'Woodford Hill'], 'Saint John': ['Portsmouth', 'Glanvillia'], 'Saint Peter': ['Colihaut', 'Dublanc'], 'Saint Patrick': ['Berekua', 'Grand Bay']},
    ),
    'DO': CountryLocationConfig(
        region_label='Province',
        subregion_label='Municipality',
        regions=['Azua', 'Bahoruco', 'Barahona', 'Dajabón', 'Distrito Nacional', 'Duarte', 'El Seibo', 'Elías Piña', 'Espaillat', 'Hato Mayor', 'Hermanas Mirabal', 'Independencia', 'La Altagracia', 'La Romana', 'La Vega', 'María Trinidad Sánchez', 'Monseñor Nouel', 'Monte Cristi', 'Monte Plata', 'Pedernales', 'Peravia', 'Puerto Plata', 'Samaná', 'San Cristóbal', 'San José de Ocoa', 'San Juan', 'San Pedro de Macorís', 'Sánchez Ramírez', 'Santiago', 'Santiago Rodríguez', 'Santo Domingo', 'Valverde', 'Cibao Nordeste', 'Cibao Noroeste', 'Cibao Norte', 'Cibao Sur', 'El Valle', 'Enriquillo', 'Higuamo', 'Ozama', 'Valdesia', 'Yuma'],
        subregions={'Distrito Nacional': ['Santo Domingo City'], 'Santo Domingo': ['Santo Domingo Este', 'Santo Domingo Norte', 'Santo Domingo Oeste', 'Boca Chica'], 'Santiago': ['Santiago de los Caballeros', 'Villa Bisono', 'Moca'], 'La Altagracia': ['Higüey', 'San Rafael del Yuma'], 'La Romana': ['La Romana City', 'San Pedro de Macorís City']},
    ),
    'DZ': CountryLocationConfig(
        region_label='Province',
        subregion_label='District',
        regions=['Algiers', 'Oran', 'Constantine', 'Adrar', 'Chlef', 'Laghouat', 'Oum el Bouaghi', 'Batna', 'Béjaïa', 'Biskra', 'Béchar', 'Blida', 'Bouira', 'Tamanrasset', 'Tébessa', 'Tlemcen', 'Tiaret', 'Tizi Ouzou', 'Alger', 'Djelfa', 'Jijel', 'Sétif', 'Saïda', 'Skikda', 'Sidi Bel Abbès', 'Annaba', 'Guelma', 'Médéa', 'Mostaganem', "M'sila", 'Mascara', 'Ouargla', 'El Bayadh', 'Illizi', 'Bordj Bou Arréridj', 'Boumerdès', 'El Tarf', 'Tindouf', 'Tissemsilt', 'El Oued', 'Khenchela', 'Souk Ahras', 'Tipaza', 'Mila', 'Aïn Defla', 'Naama', 'Aïn Témouchent', 'Ghardaïa', 'Relizane', 'Timimoun', 'Bordj Badji Mokhtar', 'Ouled Djellal', 'Béni Abbès', 'In Salah', 'In Guezzam', 'Touggourt', 'Djanet', 'El Meghaier', 'El Meniaa'],
        subregions={},
    ),
    'EC': CountryLocationConfig(
        region_label='Province',
        subregion_label='Canton',
        regions=['Azuay', 'Bolívar', 'Cañar', 'Carchi', 'Chimborazo', 'Cotopaxi', 'El Oro', 'Esmeraldas', 'Galápagos', 'Guayas', 'Imbabura', 'Loja', 'Los Ríos', 'Manabí', 'Morona Santiago', 'Napo', 'Orellana', 'Pastaza', 'Pichincha', 'Santa Elena', 'Santo Domingo de los Tsáchilas', 'Sucumbíos', 'Tungurahua', 'Zamora Chinchipe'],
        subregions={'Pichincha': ['Quito', 'Cayambe', 'Mejía', 'Pedro Moncayo', 'Rumiñahui'], 'Guayas': ['Guayaquil', 'Samborondón', 'Durán', 'Daule', 'Milagro'], 'Azuay': ['Cuenca', 'Gualaceo', 'Paute', 'Sigsig'], 'Manabí': ['Portoviejo', 'Manta', 'Chone', 'El Carmen', 'Jipijapa'], 'El Oro': ['Machala', 'Santa Rosa', 'Pasaje', 'Huaquillas'], 'Tungurahua': ['Ambato', 'Baños', 'Pelileo', 'Tisaleo']},
    ),
    'EE': CountryLocationConfig(
        region_label='County',
        subregion_label='Municipality',
        regions=['Harju', 'Hiiu', 'Ida-Viru', 'Järva', 'Jõgeva', 'Lääne', 'Lääne-Viru', 'Põlva', 'Pärnu', 'Rapla', 'Saare', 'Tartu', 'Valga', 'Viljandi', 'Võru', 'Harjumaa', 'Hiiumaa', 'Ida-Virumaa', 'Jõgevamaa', 'Järvamaa', 'Läänemaa', 'Lääne-Virumaa', 'Põlvamaa', 'Pärnumaa', 'Raplamaa', 'Saaremaa', 'Tartumaa', 'Valgamaa', 'Viljandimaa', 'Võrumaa'],
        subregions={'Harju': ['Tallinn', 'Maardu', 'Saue', 'Keila', 'Paldiski'], 'Tartu': ['Tartu City', 'Elva', 'Võru City'], 'Ida-Viru': ['Narva', 'Kohtla-Järve', 'Sillamäe', 'Jõhvi'], 'Pärnu': ['Pärnu City', 'Paide'], 'Lääne-Viru': ['Rakvere', 'Tapa']},
    ),
    'EG': CountryLocationConfig(
        region_label='Governorate',
        subregion_label='District',
        regions=['Cairo', 'Alexandria', 'Giza', 'Al Iskandarīyah', 'Aswān', 'Asyūţ', 'Al Baḩr al Aḩmar', 'Al Buḩayrah', 'Banī Suwayf', 'Al Qāhirah', 'Ad Daqahlīyah', 'Dumyāţ', 'Al Fayyūm', 'Al Gharbīyah', 'Al Jīzah', "Al Ismā'īlīyah", "Janūb Sīnā'", 'Al Qalyūbīyah', 'Kafr ash Shaykh', 'Qinā', 'Al Uqşur', 'Al Minyā', 'Al Minūfīyah', 'Maţrūḩ', 'Būr Sa‘īd', 'Sūhāj', 'Ash Sharqīyah', "Shamāl Sīnā'", 'As Suways', 'Al Wādī al Jadīd'],
        subregions={},
    ),
    'EH': CountryLocationConfig(
        region_label='Territory',
        subregion_label='Locality',
        regions=['Western Sahara'],
        subregions={},
    ),
    'ER': CountryLocationConfig(
        region_label='Region',
        subregion_label='Sub-Region',
        regions=['Maekel', 'Debub', 'Anseba', 'Ansabā', 'Debubawi K’eyyĭḥ Baḥri', 'Al Janūbī', 'Gash-Barka', 'Al Awsaţ', 'Semienawi K’eyyĭḥ Baḥri'],
        subregions={},
    ),
    'ES': CountryLocationConfig(
        region_label='Autonomous Community',
        subregion_label='Province',
        regions=['Madrid', 'Catalonia', 'Andalusia', 'Andalucía', 'Aragón', 'Asturias, Principado de', 'Cantabria', 'Ceuta', 'Castilla y León', 'Castilla-La Mancha', 'Canarias', 'Catalunya [Cataluña]', 'Extremadura', 'Galicia [Galicia]', 'Illes Balears [Islas Baleares]', 'Murcia, Región de', 'Madrid, Comunidad de', 'Melilla', 'Nafarroako Foru Komunitatea*', 'Euskal Herria', 'La Rioja', 'Valenciana, Comunidad'],
        subregions={},
    ),
    'ET': CountryLocationConfig(
        region_label='Region',
        subregion_label='Zone',
        regions=['Addis Ababa', 'Oromia', 'Amhara', 'Afar', 'Amara', 'Benshangul-Gumaz', 'Dire Dawa', 'Gambela Peoples', 'Harari People', 'Sidama', 'Southern Nations, Nationalities and Peoples', 'Somali', 'Southwest Ethiopia Peoples', 'Tigrai'],
        subregions={},
    ),
    'FI': CountryLocationConfig(
        region_label='Region',
        subregion_label='Municipality',
        regions=['Åland Islands', 'Central Finland', 'Central Ostrobothnia', 'Finland Proper', 'Kainuu', 'Kymenlaakso', 'Lapland', 'North Karelia', 'North Ostrobothnia', 'North Savo', 'Ostrobothnia', 'Päijänne Tavastia', 'Pirkanmaa', 'Satakunta', 'South Karelia', 'South Ostrobothnia', 'South Savo', 'Tavastia Proper', 'Uusimaa', 'Landskapet Åland', 'Etelä-Karjala', 'Etelä-Pohjanmaa', 'Etelä-Savo', 'Kanta-Häme', 'Keski-Pohjanmaa', 'Keski-Suomi', 'Lappi', 'Pohjanmaa', 'Pohjois-Karjala', 'Pohjois-Pohjanmaa', 'Pohjois-Savo', 'Päijät-Häme', 'Varsinais-Suomi'],
        subregions={'Uusimaa': ['Helsinki', 'Espoo', 'Vantaa', 'Tampere', 'Porvoo'], 'Pirkanmaa': ['Tampere', 'Nokia', 'Ylöjärvi', 'Kangasala'], 'Finland Proper': ['Turku', 'Salo', 'Naantali', 'Raisio'], 'North Ostrobothnia': ['Oulu', 'Raahe', 'Ylivieska', 'Oulainen'], 'Lapland': ['Rovaniemi', 'Kemi', 'Tornio', 'Kemijärvi'], 'Central Finland': ['Jyväskylä', 'Jämsä', 'Keuruu']},
    ),
    'FJ': CountryLocationConfig(
        region_label='Division',
        subregion_label='Province',
        regions=['Central', 'Eastern', 'Northern', 'Western', 'Rotuma'],
        subregions={'Central': ['Suva', 'Nausori', 'Navua', 'Korovou', 'Levuka'], 'Western': ['Lautoka', 'Nadi', 'Ba', 'Sigatoka', 'Tavua'], 'Northern': ['Labasa', 'Savusavu', 'Seaqaqa'], 'Eastern': ['Levuka Town', 'Lomaiviti', 'Lau', 'Kadavu']},
    ),
    'FK': CountryLocationConfig(
        region_label='Territory',
        subregion_label='Locality',
        regions=['Falkland Islands (Malvinas)'],
        subregions={},
    ),
    'FM': CountryLocationConfig(
        region_label='State',
        subregion_label='Municipality',
        regions=['Chuuk', 'Kosrae', 'Pohnpei', 'Yap'],
        subregions={'Pohnpei': ['Palikir', 'Kolonia', 'Kitti', 'Madolenihmw'], 'Chuuk': ['Weno', 'Faichuk', 'Ruo'], 'Yap': ['Colonia', 'Tomil-Gagil', 'Map'], 'Kosrae': ['Tofol', 'Lelu', 'Malem']},
    ),
    'FO': CountryLocationConfig(
        region_label='Territory',
        subregion_label='Locality',
        regions=['Faroe Islands'],
        subregions={},
    ),
    'FR': CountryLocationConfig(
        region_label='Region',
        subregion_label='Department',
        regions=['Île-de-France', "Provence-Alpes-Côte d'Azur", 'Auvergne-Rhône-Alpes', 'Corse', 'Guadeloupe', 'Martinique', 'Guyane (française)', 'La Réunion', 'Mayotte', 'Bourgogne-Franche-Comté', 'Saint-Barthélemy', 'Bretagne', 'Clipperton', 'Centre-Val de Loire', 'Grand-Est', 'Hauts-de-France', 'Saint-Martin', 'Nouvelle-Aquitaine', 'Nouvelle-Calédonie', 'Normandie', 'Occitanie', 'Pays-de-la-Loire', 'Polynésie française', 'Saint-Pierre-et-Miquelon', 'Terres australes françaises', 'Wallis-et-Futuna'],
        subregions={},
    ),
    'GA': CountryLocationConfig(
        region_label='Province',
        subregion_label='Department',
        regions=['Estuaire', 'Haut-Ogooué', 'Woleu-Ntem', 'Moyen-Ogooué', 'Ngounié', 'Nyanga', 'Ogooué-Ivindo', 'Ogooué-Lolo', 'Ogooué-Maritime'],
        subregions={},
    ),
    'GB': CountryLocationConfig(
        region_label='Country',
        subregion_label='District',
        regions=['England', 'Scotland', 'Wales', 'Northern Ireland', 'Wales [Cymru GB-CYM]'],
        subregions={'England': ['Greater London', 'Greater Manchester', 'West Midlands', 'West Yorkshire', 'Merseyside'], 'Scotland': ['Glasgow City', 'City of Edinburgh', 'Aberdeen City'], 'Wales': ['Cardiff', 'Swansea', 'Newport'], 'Northern Ireland': ['Belfast', 'Derry and Strabane']},
    ),
    'GD': CountryLocationConfig(
        region_label='Parish',
        subregion_label='Village',
        regions=['Saint Andrew', 'Saint David', 'Saint George', 'Saint John', 'Saint Mark', 'Saint Patrick', 'Carriacou and Petite Martinique', 'Southern Grenadine Islands'],
        subregions={'Saint George': ["St. George's City", 'Grand Anse', 'Calliste'], 'Saint Andrew': ['Grenville', 'Birchgrove'], 'Saint Patrick': ['Sauteurs', 'Victoria'], 'Carriacou and Petite Martinique': ['Hillsborough']},
    ),
    'GE': CountryLocationConfig(
        region_label='Region',
        subregion_label='Municipality',
        regions=['Adjara', 'Guria', 'Imereti', 'Kakheti', 'Kvemo Kartli', 'Mtskheta-Mtianeti', 'Racha-Lechkhumi and Kvemo Svaneti', 'Samegrelo-Zemo Svaneti', 'Samtskhe-Javakheti', 'Shida Kartli', 'Tbilisi', 'Abkhazia', 'Ajaria', "K'akheti", "Rach'a-Lechkhumi-Kvemo Svaneti"],
        subregions={'Tbilisi': ['Tbilisi City'], 'Adjara': ['Batumi', 'Kobuleti', 'Khelvachauri', 'Keda'], 'Imereti': ['Kutaisi', 'Zestaponi', 'Samtredia', 'Chiatura'], 'Kakheti': ['Telavi', 'Akhmeta', 'Gurjaani', 'Lagodekhi'], 'Kvemo Kartli': ['Rustavi', 'Gardabani', 'Marneuli', 'Bolnisi'], 'Shida Kartli': ['Gori', 'Kaspi', 'Kareli'], 'Mtskheta-Mtianeti': ['Mtskheta', 'Dusheti', 'Tianeti']},
    ),
    'GF': CountryLocationConfig(
        region_label='Territory',
        subregion_label='Locality',
        regions=['French Guiana'],
        subregions={},
    ),
    'GG': CountryLocationConfig(
        region_label='Territory',
        subregion_label='Locality',
        regions=['Guernsey'],
        subregions={},
    ),
    'GH': CountryLocationConfig(
        region_label='Region',
        subregion_label='District',
        regions=['Greater Accra', 'Ashanti', 'Western', 'Ahafo', 'Bono East', 'Bono', 'Central', 'Eastern', 'North East', 'Northern', 'Oti', 'Savannah', 'Volta', 'Upper East', 'Upper West', 'Western North'],
        subregions={},
    ),
    'GI': CountryLocationConfig(
        region_label='Territory',
        subregion_label='Locality',
        regions=['Gibraltar'],
        subregions={},
    ),
    'GL': CountryLocationConfig(
        region_label='Municipality',
        subregion_label='District',
        regions=['Avannaata Kommunia', 'Kommune Kujalleq', 'Qeqqata Kommunia', 'Kommune Qeqertalik', 'Kommuneqarfik Sermersooq'],
        subregions={},
    ),
    'GM': CountryLocationConfig(
        region_label='Division',
        subregion_label='District',
        regions=['Banjul', 'Kanifing', 'West Coast', 'Lower River', 'Central River', 'North Bank', 'Upper River', 'Western'],
        subregions={},
    ),
    'GN': CountryLocationConfig(
        region_label='Region',
        subregion_label='Prefecture',
        regions=['Conakry', 'Boké', 'Kankan', 'Kindia', 'Faranah', 'Labé', 'Mamou', 'Nzérékoré'],
        subregions={},
    ),
    'GP': CountryLocationConfig(
        region_label='Territory',
        subregion_label='Locality',
        regions=['Guadeloupe'],
        subregions={},
    ),
    'GQ': CountryLocationConfig(
        region_label='Province',
        subregion_label='District',
        regions=['Litoral', 'Kie-Ntem', 'Bioko Norte', 'Région Continentale', 'Région Insulaire'],
        subregions={},
    ),
    'GR': CountryLocationConfig(
        region_label='Region',
        subregion_label='Municipality',
        regions=['Attica', 'Central Greece', 'Central Macedonia', 'Crete', 'Eastern Macedonia and Thrace', 'Epirus', 'Ionian Islands', 'North Aegean', 'Peloponnese', 'South Aegean', 'Thessaly', 'Western Greece', 'Western Macedonia', 'Mount Athos', 'Ágion Óros', 'Anatolikí Makedonía kai Thráki', 'Kentrikí Makedonía', 'Dytikí Makedonía', 'Ípeiros', 'Thessalía', 'Ionía Nísia', 'Dytikí Elláda', 'Stereá Elláda', 'Attikí', 'Pelopónnisos', 'Vóreio Aigaío', 'Nótio Aigaío', 'Kríti'],
        subregions={'Attica': ['Athens', 'Piraeus', 'Peristeri', 'Kallithea', 'Nikaia'], 'Central Macedonia': ['Thessaloniki', 'Kalamaria', 'Pavlos Melas', 'Ampelokipoi'], 'Crete': ['Heraklion', 'Chania', 'Rethymno', 'Agios Nikolaos'], 'Thessaly': ['Larissa', 'Volos', 'Trikala', 'Karditsa'], 'Peloponnese': ['Patras', 'Tripoli', 'Kalamata', 'Corinth'], 'Epirus': ['Ioannina', 'Arta', 'Preveza', 'Thesprotia']},
    ),
    'GS': CountryLocationConfig(
        region_label='Territory',
        subregion_label='Locality',
        regions=['South Georgia and the South Sandwich Islands'],
        subregions={},
    ),
    'GT': CountryLocationConfig(
        region_label='Department',
        subregion_label='Municipality',
        regions=['Alta Verapaz', 'Baja Verapaz', 'Chimaltenango', 'Chiquimula', 'El Progreso', 'Escuintla', 'Guatemala', 'Huehuetenango', 'Izabal', 'Jalapa', 'Jutiapa', 'Petén', 'Quetzaltenango', 'Quiché', 'Retalhuleu', 'Sacatepéquez', 'San Marcos', 'Santa Rosa', 'Sololá', 'Suchitepéquez', 'Totonicapán', 'Zacapa'],
        subregions={'Guatemala': ['Guatemala City', 'Mixco', 'Villa Nueva', 'San Juan Sacatepéquez'], 'Quetzaltenango': ['Quetzaltenango City', 'Coatepeque', 'San Marcos City'], 'Escuintla': ['Escuintla City', 'Puerto San José', 'Masagua'], 'Petén': ['Flores', 'San Benito', 'La Libertad'], 'Izabal': ['Puerto Barrios', 'Morales', 'El Estor']},
    ),
    'GU': CountryLocationConfig(
        region_label='Territory',
        subregion_label='Locality',
        regions=['Guam'],
        subregions={},
    ),
    'GW': CountryLocationConfig(
        region_label='Region',
        subregion_label='Sector',
        regions=['Bissau', 'Bafatá', 'Gabú', 'Leste', 'Norte', 'Sul'],
        subregions={},
    ),
    'GY': CountryLocationConfig(
        region_label='Region',
        subregion_label='Municipality',
        regions=['Barima-Waini', 'Cuyuni-Mazaruni', 'Demerara-Mahaica', 'East Berbice-Corentyne', 'Essequibo Islands-West Demerara', 'Mahaica-Berbice', 'Pomeroon-Supenaam', 'Potaro-Siparuni', 'Upper Demerara-Berbice', 'Upper Takutu-Upper Essequibo'],
        subregions={'Demerara-Mahaica': ['Georgetown', 'Agricola', 'Timehri'], 'East Berbice-Corentyne': ['New Amsterdam', 'Berbice', 'Corriverton'], 'Essequibo Islands-West Demerara': ['Vreed-en-Hoop', 'Parika'], 'Mahaica-Berbice': ['Rosignol', 'Fort Wellington'], 'Barima-Waini': ['Mabaruma', 'Port Kaituma']},
    ),
    'HK': CountryLocationConfig(
        region_label='Territory',
        subregion_label='Locality',
        regions=['Hong Kong'],
        subregions={},
    ),
    'HM': CountryLocationConfig(
        region_label='Territory',
        subregion_label='Locality',
        regions=['Heard Island and McDonald Islands'],
        subregions={},
    ),
    'HN': CountryLocationConfig(
        region_label='Department',
        subregion_label='Municipality',
        regions=['Atlántida', 'Choluteca', 'Colón', 'Comayagua', 'Copán', 'Cortés', 'El Paraíso', 'Francisco Morazán', 'Gracias a Dios', 'Intibucá', 'Islas de la Bahía', 'La Paz', 'Lempira', 'Ocotepeque', 'Olancho', 'Santa Bárbara', 'Valle', 'Yoro'],
        subregions={'Francisco Morazán': ['Tegucigalpa', 'Distrito Central', 'Talanga', 'Valle de Ángeles'], 'Cortés': ['San Pedro Sula', 'Puerto Cortés', 'Choloma', 'La Lima'], 'Atlántida': ['La Ceiba', 'Tela', 'La Masica'], 'Comayagua': ['Comayagua City', 'Siguatepeque', 'Villanueva'], 'Olancho': ['Juticalpa', 'Catacamas', 'Salamá']},
    ),
    'HR': CountryLocationConfig(
        region_label='County',
        subregion_label='Municipality',
        regions=['Bjelovar-Bilogora', 'Brod-Posavina', 'Dubrovnik-Neretva', 'Istria', 'Karlovac', 'Koprivnica-Križevci', 'Krapina-Zagorje', 'Lika-Senj', 'Međimurje', 'Osijek-Baranja', 'Požega-Slavonia', 'Primorje-Gorski Kotar', 'Šibenik-Knin', 'Sisak-Moslavina', 'Split-Dalmatia', 'Varaždin', 'Virovitica-Podravina', 'Vukovar-Srijem', 'Zadar', 'Zagreb County', 'Zagreb City', 'Zagrebačka županija', 'Krapinsko-zagorska županija', 'Sisačko-moslavačka županija', 'Karlovačka županija', 'Varaždinska županija', 'Koprivničko-križevačka županija', 'Bjelovarsko-bilogorska županija', 'Primorsko-goranska županija', 'Ličko-senjska županija', 'Virovitičko-podravska županija', 'Požeško-slavonska županija', 'Brodsko-posavska županija', 'Zadarska županija', 'Osječko-baranjska županija', 'Šibensko-kninska županija', 'Vukovarsko-srijemska županija', 'Splitsko-dalmatinska županija', 'Istarska županija', 'Dubrovačko-neretvanska županija', 'Međimurska županija', 'Grad Zagreb'],
        subregions={'Zagreb City': ['Zagreb City'], 'Split-Dalmatia': ['Split', 'Kaštela', 'Solin', 'Trogir', 'Makarska'], 'Primorje-Gorski Kotar': ['Rijeka', 'Opatija', 'Crikvenica', 'Krk'], 'Osijek-Baranja': ['Osijek', 'Đakovo', 'Vinkovci'], 'Istria': ['Pula', 'Poreč', 'Rovinj', 'Umag'], 'Zadar': ['Zadar City', 'Biograd na Moru'], 'Dubrovnik-Neretva': ['Dubrovnik', 'Metković', 'Korčula']},
    ),
    'HT': CountryLocationConfig(
        region_label='Department',
        subregion_label='Arrondissement',
        regions=['Artibonite', 'Centre', "Grand'Anse", 'Nippes', 'Nord', 'Nord-Est', 'Nord-Ouest', 'Ouest', 'Sud', 'Sud-Est', 'Grande’Anse'],
        subregions={'Ouest': ['Port-au-Prince', 'Croix-des-Bouquets', 'Léogâne', 'Arcahaie'], 'Nord': ['Cap-Haïtien', 'Acul-du-Nord', 'Grande-Rivière-du-Nord'], 'Artibonite': ['Gonaïves', 'Saint-Marc', 'Dessalines', 'Gros-Morne'], 'Sud': ['Les Cayes', 'Aquin', 'Camp-Perrin'], 'Centre': ['Hinche', 'Mirebalais', 'Lascahobas']},
    ),
    'HU': CountryLocationConfig(
        region_label='County',
        subregion_label='City',
        regions=['Baranya', 'Bács-Kiskun', 'Békés', 'Borsod-Abaúj-Zemplén', 'Budapest', 'Csongrád-Csanád', 'Fejér', 'Győr-Moson-Sopron', 'Hajdú-Bihar', 'Heves', 'Jász-Nagykun-Szolnok', 'Komárom-Esztergom', 'Nógrád', 'Pest', 'Somogy', 'Szabolcs-Szatmár-Bereg', 'Tolna', 'Vas', 'Veszprém', 'Zala', 'Békéscsaba', 'Debrecen', 'Dunaújváros', 'Eger', 'Érd', 'Győr', 'Hódmezővásárhely', 'Kecskemét', 'Kaposvár', 'Miskolc', 'Nagykanizsa', 'Nyíregyháza', 'Pécs', 'Szeged', 'Székesfehérvár', 'Szombathely', 'Szolnok', 'Sopron', 'Szekszárd', 'Salgótarján', 'Tatabánya', 'Zalaegerszeg'],
        subregions={'Budapest': ['Budapest City'], 'Pest': ['Érd', 'Gödöllő', 'Dunakeszi', 'Vác'], 'Borsod-Abaúj-Zemplén': ['Miskolc', 'Kazincbarcika', 'Ózd', 'Tiszaújváros'], 'Győr-Moson-Sopron': ['Győr', 'Sopron', 'Mosonmagyaróvár'], 'Hajdú-Bihar': ['Debrecen', 'Nyíregyháza', 'Hajdúböszörmény'], 'Bács-Kiskun': ['Kecskemét', 'Baja', 'Kiskunfélegyháza'], 'Csongrád-Csanád': ['Szeged', 'Hódmezővásárhely', 'Szentes']},
    ),
    'ID': CountryLocationConfig(
        region_label='Province',
        subregion_label='Regency',
        regions=['Aceh', 'Bali', 'Bangka Belitung Islands', 'Banten', 'Bengkulu', 'Central Java', 'Central Kalimantan', 'Central Papua', 'Central Sulawesi', 'East Java', 'East Kalimantan', 'East Nusa Tenggara', 'Gorontalo', 'Highland Papua', 'Jambi', 'Jakarta', 'Lampung', 'Maluku', 'North Kalimantan', 'North Maluku', 'North Sulawesi', 'North Sumatra', 'Papua', 'Riau', 'Riau Islands', 'Southeast Sulawesi', 'South Kalimantan', 'South Papua', 'South Sulawesi', 'South Sumatra', 'Southwest Papua', 'West Java', 'West Kalimantan', 'West Nusa Tenggara', 'West Papua', 'West Sulawesi', 'West Sumatra', 'Yogyakarta', 'Jawa', 'Kalimantan', 'Nusa Tenggara', 'Sulawesi', 'Sumatera'],
        subregions={'Jakarta': ['Central Jakarta', 'East Jakarta', 'North Jakarta', 'South Jakarta', 'West Jakarta'], 'West Java': ['Bandung', 'Bekasi', 'Bogor', 'Depok', 'Tangerang'], 'East Java': ['Surabaya', 'Malang', 'Sidoarjo', 'Gresik', 'Pasuruan'], 'Central Java': ['Semarang', 'Solo', 'Yogyakarta', 'Magelang', 'Salatiga'], 'North Sumatra': ['Medan', 'Binjai', 'Tebing Tinggi', 'Pematang Siantar'], 'South Sulawesi': ['Makassar', 'Palopo', 'Pare-Pare'], 'Bali': ['Denpasar', 'Badung', 'Gianyar', 'Tabanan']},
    ),
    'IE': CountryLocationConfig(
        region_label='Province',
        subregion_label='County',
        regions=['Connacht', 'Leinster', 'Munster', 'Ulster', 'Connaught'],
        subregions={'Leinster': ['Dublin', 'Wicklow', 'Kildare', 'Meath', 'Louth', 'Wexford', 'Carlow', 'Kilkenny', 'Offaly', 'Laois', 'Westmeath', 'Longford'], 'Munster': ['Cork', 'Kerry', 'Limerick', 'Tipperary', 'Waterford', 'Clare'], 'Connacht': ['Galway', 'Mayo', 'Roscommon', 'Sligo', 'Leitrim'], 'Ulster': ['Donegal', 'Cavan', 'Monaghan']},
    ),
    'IL': CountryLocationConfig(
        region_label='District',
        subregion_label='Sub-District',
        regions=['Central', 'Haifa', 'Jerusalem', 'Northern', 'Southern', 'Tel Aviv', 'Al Janūbī', 'H̱efa', 'Al Quds', 'Al Awsaţ', 'Tall Abīb', 'Ash Shamālī'],
        subregions={'Tel Aviv': ['Tel Aviv City', 'Ramat Gan', 'Petah Tikva', 'Bnei Brak', 'Holon'], 'Jerusalem': ['Jerusalem City', 'Bethlehem', 'Jericho'], 'Central': ['Rishon LeZion', 'Rehovot', 'Ashdod', 'Bat Yam', 'Herzliya'], 'Haifa': ['Haifa City', 'Netanya', 'Acre'], 'Northern': ['Safed', 'Tiberias', 'Nazareth', 'Nahariya'], 'Southern': ['Beer Sheva', 'Eilat', 'Arad', 'Dimona']},
    ),
    'IM': CountryLocationConfig(
        region_label='Territory',
        subregion_label='Locality',
        regions=['Isle of Man'],
        subregions={},
    ),
    'IN': CountryLocationConfig(
        region_label='State',
        subregion_label='District',
        regions=['Andhra Pradesh', 'Bihar', 'Delhi', 'Gujarat', 'Karnataka', 'Kerala', 'Maharashtra', 'Punjab', 'Rajasthan', 'Tamil Nadu', 'Uttar Pradesh', 'West Bengal', 'Andaman and Nicobar Islands', 'Arunāchal Pradesh', 'Assam', 'Chhattīsgarh', 'Chandīgarh', 'Dādra and Nagar Haveli and Damān and Diu', 'Goa', 'Himāchal Pradesh', 'Haryāna', 'Jhārkhand', 'Jammu and Kashmīr', 'Ladākh', 'Lakshadweep', 'Meghālaya', 'Manipur', 'Madhya Pradesh', 'Mizoram', 'Nāgāland', 'Odisha', 'Puducherry', 'Sikkim', 'Tripura', 'Telangāna', 'Uttarākhand'],
        subregions={'Maharashtra': ['Mumbai City', 'Pune', 'Nagpur', 'Nashik'], 'Karnataka': ['Bengaluru Urban', 'Mysuru', 'Mangaluru'], 'Delhi': ['New Delhi', 'North Delhi', 'South Delhi']},
    ),
    'IO': CountryLocationConfig(
        region_label='Territory',
        subregion_label='Locality',
        regions=['British Indian Ocean Territory'],
        subregions={},
    ),
    'IQ': CountryLocationConfig(
        region_label='Governorate',
        subregion_label='District',
        regions=['Al Anbar', 'Al Muthanna', 'Al Qādisiyyah', 'An Najaf', 'Arbil', 'As Sulaymaniyyah', 'Babil', 'Baghdad', 'Basra', 'Dahuk', 'Dhi Qar', 'Diyala', 'Karbala', 'Kirkuk', 'Maysan', 'Nineveh', 'Saladin', 'Wasit', 'Al Başrah', 'Herêm-î Kurdistan', 'Nīnawá', 'Al Qādisīyah', 'Şalāḩ ad Dīn'],
        subregions={'Baghdad': ['Baghdad City', 'Abu Ghraib', 'Al-Madain', 'Tarmiyah'], 'Basra': ['Basra City', 'Abu Al-Khasib', 'Qurna', 'Shatt Al-Arab'], 'Nineveh': ['Mosul', 'Sinjar', 'Telafar', 'Hamdaniya'], 'Arbil': ['Erbil City', 'Makhmur', 'Shaqlawa', 'Mergasor'], 'Karbala': ['Karbala City', 'Ain Al-Tamr'], 'An Najaf': ['Najaf City', 'Al Kufa', 'Al Manathira']},
    ),
    'IR': CountryLocationConfig(
        region_label='Province',
        subregion_label='County',
        regions=['Alborz', 'Ardabil', 'Bushehr', 'Chaharmahal and Bakhtiari', 'East Azerbaijan', 'Fars', 'Gilan', 'Golestan', 'Hamadan', 'Hormozgan', 'Ilam', 'Isfahan', 'Kerman', 'Kermanshah', 'Khuzestan', 'Kohgiluyeh and Boyer-Ahmad', 'Kurdistan', 'Lorestan', 'Markazi', 'Mazandaran', 'North Khorasan', 'Qazvin', 'Qom', 'Razavi Khorasan', 'Semnan', 'Sistan and Baluchestan', 'South Khorasan', 'Tehran', 'West Azerbaijan', 'Yazd', 'Zanjan', 'Āz̄ārbāyjān-e Shārqī', 'Āz̄ārbāyjān-e Ghārbī', 'Khorāsān-e Raẕavī', 'Eşfahān', 'Sīstān va Balūchestān', 'Kordestān', 'Chahār Maḩāl va Bakhtīārī', 'Kohgīlūyeh va Bowyer Aḩmad', 'Khorāsān-e Shomālī', 'Khorāsān-e Jonūbī'],
        subregions={'Tehran': ['Tehran City', 'Karaj', 'Rey', 'Shemiranat', 'Islamshahr'], 'Isfahan': ['Isfahan City', 'Kashan', 'Najafabad', 'Khomeyni Shahr'], 'Razavi Khorasan': ['Mashhad', 'Nishapur', 'Sabzevar', 'Torbat-e Heydarieh'], 'Fars': ['Shiraz', 'Marvdasht', 'Kazerun', 'Jahrom'], 'East Azerbaijan': ['Tabriz', 'Maragheh', 'Mianeh', 'Shabestar'], 'Khuzestan': ['Ahvaz', 'Abadan', 'Khorramshahr', 'Dezful'], 'Gilan': ['Rasht', 'Lahijan', 'Anzali', 'Roudbar']},
    ),
    'IS': CountryLocationConfig(
        region_label='Region',
        subregion_label='Municipality',
        regions=['Capital Region', 'Southern Peninsula', 'West', 'Westfjords', 'Northwest', 'Northeast', 'East', 'South', 'Höfuðborgarsvæði', 'Suðurnes', 'Vesturland', 'Vestfirðir', 'Norðurland vestra', 'Norðurland eystra', 'Austurland', 'Suðurland'],
        subregions={'Capital Region': ['Reykjavík', 'Kópavogur', 'Hafnarfjörður', 'Akranes', 'Garðabær'], 'South': ['Selfoss', 'Hvolsvöllur', 'Vestmannaeyjar'], 'West': ['Akranes', 'Borgarnes'], 'Northeast': ['Akureyri', 'Húsavík', 'Dalvík'], 'East': ['Egilsstaðir', 'Reyðarfjörður', 'Neskaupstaður'], 'Northwest': ['Ísafjörður', 'Bolungarvík']},
    ),
    'IT': CountryLocationConfig(
        region_label='Region',
        subregion_label='Province',
        regions=['Lombardy', 'Lazio', 'Sicily', 'Piemonte', "Val d'Aoste", 'Lombardia', 'Trentino-Alto Adige', 'Veneto', 'Friuli Venezia Giulia', 'Liguria', 'Emilia-Romagna', 'Toscana', 'Umbria', 'Marche', 'Abruzzo', 'Molise', 'Campania', 'Puglia', 'Basilicata', 'Calabria', 'Sicilia', 'Sardegna'],
        subregions={},
    ),
    'JE': CountryLocationConfig(
        region_label='Territory',
        subregion_label='Locality',
        regions=['Jersey'],
        subregions={},
    ),
    'JM': CountryLocationConfig(
        region_label='Parish',
        subregion_label='Community',
        regions=['Clarendon', 'Hanover', 'Kingston', 'Manchester', 'Portland', 'Saint Andrew', 'Saint Ann', 'Saint Catherine', 'Saint Elizabeth', 'Saint James', 'Saint Mary', 'Saint Thomas', 'Trelawny', 'Westmoreland'],
        subregions={'Kingston': ['Kingston City', 'Half Way Tree'], 'Saint Andrew': ['Kingston Metro Area', 'Portmore'], 'Saint Catherine': ['Spanish Town', 'Portmore', 'Old Harbour'], 'Saint James': ['Montego Bay', 'Falmouth'], 'Clarendon': ['May Pen', 'Chapelton']},
    ),
    'JO': CountryLocationConfig(
        region_label='Governorate',
        subregion_label='District',
        regions=['Ajloun', 'Aqaba', 'Balqa', 'Irbid', 'Jarash', 'Karak', "Ma'an", 'Madaba', 'Mafraq', 'Amman', 'Tafilah', 'Zarqa', '‘Ajlūn', 'Al ‘A̅şimah', 'Al ‘Aqabah', 'Aţ Ţafīlah', 'Az Zarqā’', 'Al Balqā’', 'Al Karak', 'Al Mafraq'],
        subregions={'Amman': ['Amman City', 'Wadi Seer', 'Sahab', 'Naur', 'Muwaqqar'], 'Zarqa': ['Zarqa City', 'Russeifa', 'Azraq'], 'Irbid': ['Irbid City', 'Ramtha', 'Bani Kananah', 'Koura'], 'Aqaba': ['Aqaba City'], 'Balqa': ['Salt', 'Madaba City', 'Shouneh'], 'Mafraq': ['Mafraq City', 'Badia']},
    ),
    'JP': CountryLocationConfig(
        region_label='Prefecture',
        subregion_label='Municipality',
        regions=['Aichi', 'Akita', 'Aomori', 'Chiba', 'Ehime', 'Fukui', 'Fukuoka', 'Fukushima', 'Gifu', 'Gunma', 'Hiroshima', 'Hokkaido', 'Hyogo', 'Ibaraki', 'Ishikawa', 'Iwate', 'Kagawa', 'Kagoshima', 'Kanagawa', 'Kochi', 'Kumamoto', 'Kyoto', 'Mie', 'Miyagi', 'Miyazaki', 'Nagano', 'Nagasaki', 'Nara', 'Niigata', 'Oita', 'Okayama', 'Okinawa', 'Osaka', 'Saga', 'Saitama', 'Shiga', 'Shimane', 'Shizuoka', 'Tochigi', 'Tokushima', 'Tokyo', 'Tottori', 'Toyama', 'Wakayama', 'Yamagata', 'Yamaguchi', 'Yamanashi'],
        subregions={'Tokyo': ['Shinjuku', 'Shibuya', 'Chiyoda', 'Minato', 'Sumida', 'Setagaya'], 'Osaka': ['Osaka City', 'Sakai', 'Higashiosaka', 'Hirakata', 'Toyonaka'], 'Kanagawa': ['Yokohama', 'Kawasaki', 'Sagamihara', 'Kamakura', 'Fujisawa'], 'Aichi': ['Nagoya', 'Toyohashi', 'Okazaki', 'Ichinomiya', 'Toyota'], 'Fukuoka': ['Fukuoka City', 'Kitakyushu', 'Kurume', 'Kasuga', 'Omuta'], 'Hokkaido': ['Sapporo', 'Asahikawa', 'Hakodate', 'Kushiro', 'Obihiro'], 'Hyogo': ['Kobe', 'Himeji', 'Amagasaki', 'Nishimomiya', 'Akashi'], 'Kyoto': ['Kyoto City', 'Uji', 'Kameoka'], 'Saitama': ['Saitama City', 'Kawaguchi', 'Kawagoe', 'Tokorozawa'], 'Chiba': ['Chiba City', 'Funabashi', 'Matsudo', 'Ichikawa']},
    ),
    'KE': CountryLocationConfig(
        region_label='County',
        subregion_label='Sub-County',
        regions=['Nairobi', 'Mombasa', 'Kisumu', 'Baringo', 'Bomet', 'Bungoma', 'Busia', 'Elgeyo/Marakwet', 'Embu', 'Garissa', 'Homa Bay', 'Isiolo', 'Kajiado', 'Kakamega', 'Kericho', 'Kiambu', 'Kilifi', 'Kirinyaga', 'Kisii', 'Kitui', 'Kwale', 'Laikipia', 'Lamu', 'Machakos', 'Makueni', 'Mandera', 'Marsabit', 'Meru', 'Migori', "Murang'a", 'Nairobi City', 'Nakuru', 'Nandi', 'Narok', 'Nyamira', 'Nyandarua', 'Nyeri', 'Samburu', 'Siaya', 'Taita/Taveta', 'Tana River', 'Tharaka-Nithi', 'Trans Nzoia', 'Turkana', 'Uasin Gishu', 'Vihiga', 'Wajir', 'West Pokot'],
        subregions={},
    ),
    'KG': CountryLocationConfig(
        region_label='Region',
        subregion_label='District',
        regions=['Batken', 'Bishkek City', 'Chuy', 'Issyk-Kul', 'Jalal-Abad', 'Naryn', 'Osh City', 'Osh Region', 'Talas', "Chuyskaya oblast'", 'Bishkek Shaary', 'Gorod Osh', "Dzhalal-Abadskaya oblast'", 'Osh', "Issyk-Kul'skaja oblast'"],
        subregions={'Bishkek City': ['Bishkek City'], 'Osh City': ['Osh City'], 'Chuy': ['Tokmok', 'Kant', 'Kemin', 'Sokuluk'], 'Jalal-Abad': ['Jalal-Abad City', 'Kara-Suu', 'Uzgen', 'Nooken'], 'Osh Region': ['Kara-Kuldja', 'Aravan', 'Kara-Suu'], 'Issyk-Kul': ['Karakol', 'Balykchy', 'Cholpon-Ata'], 'Naryn': ['Naryn City', 'Kochkor', 'At-Bashy']},
    ),
    'KH': CountryLocationConfig(
        region_label='Province',
        subregion_label='District',
        regions=['Banteay Meanchey', 'Battambang', 'Kampong Cham', 'Kampong Chhnang', 'Kampong Speu', 'Kampong Thom', 'Kampot', 'Kandal', 'Koh Kong', 'Kep', 'Kratie', 'Mondulkiri', 'Oddar Meanchey', 'Pailin', 'Phnom Penh', 'Preah Sihanouk', 'Preah Vihear', 'Prey Veng', 'Pursat', 'Ratanakiri', 'Siem Reap', 'Stung Treng', 'Svay Rieng', 'Takeo', 'Tbong Khmum', 'Banteay Mean Choăy', 'Kracheh', 'Mondol Kiri', 'Prey Veaeng', 'Pousaat', 'Rotanak Kiri', 'Siem Reab', 'Stoĕng Trêng', 'Baat Dambang', 'Svaay Rieng', 'Taakaev', 'Otdar Mean Chey', 'Kaeb', 'Kampong Chaam', 'Kampong Spueu', 'Kampong Thum', 'Kandaal', 'Kaoh Kong'],
        subregions={'Phnom Penh': ['Chamkarmon', 'Doun Penh', 'Prampir Meakkakra', 'Tuol Kouk', 'Dangkao'], 'Siem Reap': ['Siem Reap District', 'Angkor Chum', 'Puok', 'Prasat Bakong'], 'Battambang': ['Battambang District', 'Banan', 'Sangkae', 'Thma Koul'], 'Kampong Cham': ['Kampong Cham District', 'Batheay', 'Chamkar Leu'], 'Preah Sihanouk': ['Preah Sihanouk District', 'Kampong Seila']},
    ),
    'KI': CountryLocationConfig(
        region_label='Island Group',
        subregion_label='Island',
        regions=['Gilbert Islands', 'Line Islands', 'Phoenix Islands'],
        subregions={'Gilbert Islands': ['Tarawa', 'Abaiang', 'Abemama', 'Butaritari', 'Maiana', 'Marakei', 'Nonouti'], 'Line Islands': ['Christmas Island (Kiritimati)', 'Fanning Island', 'Washington Island'], 'Phoenix Islands': ['Canton', 'Enderbury', 'Birnie']},
    ),
    'KM': CountryLocationConfig(
        region_label='Island',
        subregion_label='Commune',
        regions=['Grande Comore', 'Anjouan', 'Mohéli'],
        subregions={},
    ),
    'KN': CountryLocationConfig(
        region_label='Parish',
        subregion_label='Village',
        regions=['Christ Church Nichola Town', 'Saint Anne Sandy Point', 'Saint George Basseterre', 'Saint George Gingerland', 'Saint James Windward', 'Saint John Capesterre', 'Saint John Figtree', 'Saint Mary Cayon', 'Saint Paul Capesterre', 'Saint Paul Charlestown', 'Saint Peter Basseterre', 'Saint Thomas Lowland', 'Saint Thomas Middle Island', 'Trinity Palmetto Point', 'Saint Kitts', 'Nevis'],
        subregions={'Saint George Basseterre': ['Basseterre'], 'Saint Paul Charlestown': ['Charlestown'], 'Saint Peter Basseterre': ['Bird Rock'], 'Saint Anne Sandy Point': ['Sandy Point'], 'Saint Thomas Middle Island': ['Middle Island']},
    ),
    'KP': CountryLocationConfig(
        region_label='Province',
        subregion_label='County',
        regions=['Chagang', 'North Hamgyong', 'South Hamgyong', 'North Hwanghae', 'South Hwanghae', 'Kangwon', 'North Pyongan', 'South Pyongan', 'Pyongyang', 'Rason', 'Ryanggang', "P'yǒngyang", "P'yǒngan-namdo", "P'yǒngan-bukto", 'Chagang-do', 'Hwanghae-namdo', 'Hwanghae-bukto', 'Kangweonto', 'Hamgyǒng-namdo', 'Hamgyǒng-bukto', 'Ryanggang-do', 'Raseon', 'Nampho', 'Kaeseong'],
        subregions={'Pyongyang': ['Pyongyang City', 'Mangyongdae', 'Moranbong', 'Taedong'], 'South Pyongan': ['Pyongsong', 'Nampho', 'Anju', 'Sunchon'], 'North Hamgyong': ['Chongjin', 'Kimchaek', 'Hoeryong', 'Musan'], 'South Hamgyong': ['Hamhung', 'Hungnam', 'Sinpho', 'Tanchon'], 'North Hwanghae': ['Sariwon', 'Sinmak', 'Phyongsan']},
    ),
    'KR': CountryLocationConfig(
        region_label='Province',
        subregion_label='City',
        regions=['Busan', 'Chungcheongbuk-do', 'Chungcheongnam-do', 'Daegu', 'Daejeon', 'Gangwon-do', 'Gwangju', 'Gyeonggi-do', 'Gyeongsangbuk-do', 'Gyeongsangnam-do', 'Incheon', 'Jeju-do', 'Jeollabuk-do', 'Jeollanam-do', 'Sejong', 'Seoul', 'Ulsan', 'Seoul-teukbyeolsi', 'Busan-gwangyeoksi', 'Daegu-gwangyeoksi', 'Incheon-gwangyeoksi', 'Gwangju-gwangyeoksi', 'Daejeon-gwangyeoksi', 'Ulsan-gwangyeoksi', 'Gangwon-teukbyeoljachido', 'Jeju-teukbyeoljachido'],
        subregions={'Seoul': ['Gangnam-gu', 'Jongno-gu', 'Jung-gu', 'Mapo-gu', 'Yeongdeungpo-gu'], 'Gyeonggi-do': ['Suwon', 'Seongnam', 'Goyang', 'Yongin', 'Bucheon'], 'Busan': ['Busan City', 'Haeundae-gu', 'Suyeong-gu', 'Dong-gu'], 'Incheon': ['Incheon City', 'Namdong-gu', 'Bupyeong-gu'], 'Daegu': ['Daegu City', 'Dalseo-gu', 'Suseong-gu'], 'Daejeon': ['Daejeon City', 'Yuseong-gu', 'Seo-gu'], 'Gwangju': ['Gwangju City', 'Buk-gu', 'Nam-gu']},
    ),
    'KW': CountryLocationConfig(
        region_label='Governorate',
        subregion_label='Area',
        regions=['Al Ahmadi', 'Al Asimah', 'Al Farwaniyah', 'Al Jahra', 'Hawalli', 'Mubarak Al-Kabeer', 'Mubārak al Kabīr'],
        subregions={'Al Asimah': ['Kuwait City', 'Shuwaikh', 'Dasman', 'Sharq'], 'Hawalli': ['Salmiya', 'Rumaithiya', 'Hawalli District', 'Bayan'], 'Al Farwaniyah': ['Farwaniyah', 'Jleeb Al-Shuyoukh', 'Khaitan', 'Omariya'], 'Al Ahmadi': ['Ahmadi', 'Mahboula', 'Mangaf', 'Fintas'], 'Al Jahra': ['Jahra City', 'Sulaibiya', 'Qasr'], 'Mubarak Al-Kabeer': ['Mubarak Al-Kabeer Area', 'Abu Halifa', 'Sabah Al-Salem']},
    ),
    'KY': CountryLocationConfig(
        region_label='Territory',
        subregion_label='Locality',
        regions=['Cayman Islands'],
        subregions={},
    ),
    'KZ': CountryLocationConfig(
        region_label='Region',
        subregion_label='District',
        regions=['Abai Region', 'Akmola Region', 'Aktobe Region', 'Almaty Region', 'Almaty City', 'Astana City', 'Atyrau Region', 'Bayqongyr', 'East Kazakhstan Region', 'Jetisu Region', 'Karaganda Region', 'Kostanay Region', 'Kyzylorda Region', 'Mangystau Region', 'North Kazakhstan Region', 'Pavlodar Region', 'Shymkent City', 'Turkistan Region', 'Ulytau Region', 'West Kazakhstan Region', 'Zhetysu Region', 'Abajskaja oblast’', "Akmolinskaja oblast'", "Aktjubinskaja oblast'", "Almatinskaja oblast'", "Atyrauskaja oblast'", 'Batys Qazaqstan oblysy', 'Zhambyl oblysy', 'Zhetisū oblysy', "Karagandinskaja oblast'", "Kostanajskaja oblast'", "Kyzylordinskaja oblast'", 'Mangghystaū oblysy', 'Pavlodar oblysy', "Severo-Kazahstanskaja oblast'", "Turkestankaya oblast'", 'Ulytauskaja oblast’', 'Shyghys Qazaqstan oblysy', 'Astana', 'Almaty', 'Shymkent'],
        subregions={'Almaty City': ['Almaty City'], 'Astana City': ['Astana City'], 'Karaganda Region': ['Karaganda', 'Temirtau', 'Balkhash', 'Zhezkazgan'], 'East Kazakhstan Region': ['Ust-Kamenogorsk', 'Semey', 'Ridder'], 'Aktobe Region': ['Aktobe City', 'Alga', 'Embi'], 'Kostanay Region': ['Kostanay City', 'Rudny', 'Lisakovsk'], 'Pavlodar Region': ['Pavlodar City', 'Ekibastuz', 'Aksu']},
    ),
    'LA': CountryLocationConfig(
        region_label='Province',
        subregion_label='District',
        regions=['Attapeu', 'Bokeo', 'Bolikhamsai', 'Champasak', 'Houaphan', 'Khammouane', 'Luang Namtha', 'Luang Prabang', 'Oudomxay', 'Phongsali', 'Sainyabuli', 'Salavan', 'Savannakhet', 'Sekong', 'Vientiane Prefecture', 'Vientiane Province', 'Xaisomboun', 'Xekong', 'Xiengkhouang', 'Attapu', 'Bolikhamxai', 'Khammouan', 'Louang Namtha', 'Louangphabang', 'Oudômxai', 'Viangchan', 'Xaignabouli', 'Xiangkhouang'],
        subregions={'Vientiane Prefecture': ['Chanthabuly', 'Sikhottabong', 'Xaysetha', 'Sisattanak', 'Naxaithong'], 'Champasak': ['Pakse', 'Pakxong', 'Mounlapamok'], 'Savannakhet': ['Kaysone Phomvihane', 'Outhoumphone'], 'Luang Prabang': ['Luang Prabang City', 'Xiengngeum', 'Phonxai'], 'Khammouane': ['Thakhek', 'Nongbok', 'Hinboun']},
    ),
    'LB': CountryLocationConfig(
        region_label='Governorate',
        subregion_label='District',
        regions=['Akkar', 'Baalbek-Hermel', 'Beirut', 'Beqaa', 'Mount Lebanon', 'Nabatieh', 'North Lebanon', 'South Lebanon', 'Aakkâr', 'Ash Shimāl', 'Bayrūt', 'Al Biqā‘', 'Al Janūb', 'Jabal Lubnān', 'An Nabaţīyah'],
        subregions={'Beirut': ['Beirut City'], 'Mount Lebanon': ['Baabda', 'Metn', 'Jbeil', 'Kesrouan', 'Chouf', 'Aley'], 'North Lebanon': ['Tripoli', 'Zgharta', 'Bsharri', 'Koura', 'Batroun', 'Miniyeh-Danniyeh'], 'South Lebanon': ['Sidon', 'Tyre', 'Jezzine'], 'Beqaa': ['Zahlé', 'West Beqaa', 'Rashaya'], 'Baalbek-Hermel': ['Baalbek', 'Hermel'], 'Nabatieh': ['Nabatieh', 'Bint Jbeil', 'Hasbaya', 'Marjeyoun'], 'Akkar': ['Halba', 'Akkar El Atika']},
    ),
    'LC': CountryLocationConfig(
        region_label='District',
        subregion_label='Village',
        regions=['Anse la Raye', 'Canaries', 'Castries', 'Choiseul', 'Dennery', 'Gros Islet', 'Laborie', 'Micoud', 'Soufrière', 'Vieux Fort'],
        subregions={'Castries': ['Castries City', 'Gros Islet Town'], 'Vieux Fort': ['Vieux Fort Town'], 'Soufrière': ['Soufrière Town'], 'Micoud': ['Micoud Village'], 'Dennery': ['Dennery Village']},
    ),
    'LI': CountryLocationConfig(
        region_label='Commune',
        subregion_label='Village',
        regions=['Balzers', 'Eschen', 'Gamprin', 'Mauren', 'Planken', 'Ruggell', 'Schaan', 'Schellenberg', 'Triesen', 'Triesenberg', 'Vaduz'],
        subregions={'Vaduz': ['Vaduz City'], 'Schaan': ['Schaan Village'], 'Balzers': ['Balzers Village'], 'Triesen': ['Triesen Village'], 'Triesenberg': ['Triesenberg Village']},
    ),
    'LK': CountryLocationConfig(
        region_label='Province',
        subregion_label='District',
        regions=['Central Province', 'Eastern Province', 'North Central Province', 'North Western Province', 'Northern Province', 'Sabaragamuwa Province', 'Southern Province', 'Uva Province', 'Western Province'],
        subregions={'Western Province': ['Colombo', 'Gampaha', 'Kalutara'], 'Central Province': ['Kandy', 'Matale', 'Nuwara Eliya'], 'Southern Province': ['Galle', 'Matara', 'Hambantota'], 'Northern Province': ['Jaffna', 'Kilinochchi', 'Mannar', 'Mullaitivu', 'Vavuniya'], 'Eastern Province': ['Ampara', 'Batticaloa', 'Trincomalee'], 'North Western Province': ['Kurunegala', 'Puttalam'], 'Uva Province': ['Badulla', 'Monaragala'], 'Sabaragamuwa Province': ['Kegalle', 'Ratnapura'], 'North Central Province': ['Anuradhapura', 'Polonnaruwa']},
    ),
    'LR': CountryLocationConfig(
        region_label='County',
        subregion_label='District',
        regions=['Montserrado', 'Bong', 'Nimba', 'Bomi', 'Grand Cape Mount', 'Grand Bassa', 'Grand Gedeh', 'Grand Kru', 'Gbarpolu', 'Lofa', 'Margibi', 'Maryland', 'River Gee', 'River Cess', 'Sinoe'],
        subregions={},
    ),
    'LS': CountryLocationConfig(
        region_label='District',
        subregion_label='Community Council',
        regions=['Maseru', 'Berea', 'Leribe', 'Botha-Bothe', 'Mafeteng', "Mohale's Hoek", 'Quthing', "Qacha's Nek", 'Mokhotlong', 'Thaba-Tseka'],
        subregions={},
    ),
    'LT': CountryLocationConfig(
        region_label='County',
        subregion_label='Municipality',
        regions=['Alytus County', 'Kaunas County', 'Klaipėda County', 'Marijampolė County', 'Panevėžys County', 'Šiauliai County', 'Tauragė County', 'Telšiai County', 'Utena County', 'Vilnius County', 'Alytaus apskritis', 'Klaipėdos apskritis', 'Kauno apskritis', 'Marijampolės apskritis', 'Panevėžio apskritis', 'Šiaulių apskritis', 'Tauragės apskritis', 'Telšių apskritis', 'Utenos apskritis', 'Vilniaus apskritis'],
        subregions={'Vilnius County': ['Vilnius City', 'Šalčininkai', 'Švenčionys', 'Trakai'], 'Kaunas County': ['Kaunas City', 'Kaišiadorys', 'Kėdainiai', 'Jonava'], 'Klaipėda County': ['Klaipėda City', 'Palanga', 'Neringa', 'Skuodas'], 'Šiauliai County': ['Šiauliai City', 'Radviliškis', 'Kelmė', 'Joniškis'], 'Panevėžys County': ['Panevėžys City', 'Biržai', 'Kupiškis'], 'Alytus County': ['Alytus City', 'Lazdijai', 'Varėna']},
    ),
    'LU': CountryLocationConfig(
        region_label='Canton',
        subregion_label='Commune',
        regions=['Capellen', 'Clervaux', 'Diekirch', 'Echternach', 'Esch-sur-Alzette', 'Grevenmacher', 'Luxembourg', 'Mersch', 'Redange', 'Remich', 'Vianden', 'Wiltz'],
        subregions={'Luxembourg': ['Luxembourg City', 'Strassen', 'Hesperange', 'Sandweiler'], 'Esch-sur-Alzette': ['Esch-sur-Alzette', 'Differdange', 'Dudelange', 'Sanem'], 'Capellen': ['Mamer', 'Kehlen', 'Garnich'], 'Mersch': ['Mersch', 'Fischbach', 'Larochette'], 'Diekirch': ['Diekirch City', 'Ettelbruck', 'Reisdorf'], 'Clervaux': ['Clervaux', 'Wincrange', 'Troisvierges']},
    ),
    'LV': CountryLocationConfig(
        region_label='Municipality',
        subregion_label='Administrative Unit',
        regions=['Adaži Municipality', 'Aizkraukle Municipality', 'Aizpute Municipality', 'Alsunga Municipality', 'Alūksne Municipality', 'Augšdaugava Municipality', 'Balvi Municipality', 'Bauska Municipality', 'Cēsis Municipality', 'Daugavpils City', 'Dobele Municipality', 'Dundaga Municipality', 'Engure Municipality', 'Gulbene Municipality', 'Jelgava City', 'Jelgava Municipality', 'Jēkabpils Municipality', 'Jūrmala City', 'Kandava Municipality', 'Kārsava Municipality', 'Ķekava Municipality', 'Krāslava Municipality', 'Kuldīga Municipality', 'Liepāja City', 'Limbaži Municipality', 'Līvāni Municipality', 'Ludza Municipality', 'Madona Municipality', 'Mārupe Municipality', 'Nīca Municipality', 'Ogre Municipality', 'Olaine Municipality', 'Preiļi Municipality', 'Priekuļi Municipality', 'Rēzekne City', 'Rēzekne Municipality', 'Rīga City', 'Ropaži Municipality', 'Rucava Municipality', 'Rugāji Municipality', 'Rūjiena Municipality', 'Salaspils Municipality', 'Saldus Municipality', 'Saulkrasti Municipality', 'Sigulda Municipality', 'Smiltene Municipality', 'Stopiņi Municipality', 'Talsi Municipality', 'Tukums Municipality', 'Vaiņode Municipality', 'Valka Municipality', 'Valmiera City', 'Varakļāni Municipality', 'Ventspils City', 'Ventspils Municipality', 'Viļaka Municipality', 'Viļāni Municipality', 'Zilupe Municipality', 'Aizkraukles novads', 'Alūksnes novads', 'Ādažu novads', 'Balvu novads', 'Bauskas novads', 'Cēsu novads', 'Dobeles novads', 'Gulbenes novads', 'Jelgavas novads', 'Jēkabpils novads', 'Krāslavas novads', 'Kuldīgas novads', 'Ķekavas novads', 'Limbažu novads', 'Līvānu novads', 'Ludzas novads', 'Madonas novads', 'Mārupes novads', 'Ogres novads', 'Olaines novads', 'Preiļu novads', 'Rēzeknes novads', 'Ropažu novads', 'Salaspils novads', 'Saldus novads', 'Saulkrastu novads', 'Siguldas novads', 'Smiltenes novads', 'Talsu novads', 'Tukuma novads', 'Valkas novads', 'Varakļānu novads', 'Ventspils novads', 'Augšdaugavas novads', 'Dienvidkurzemes Novads', 'Valmieras Novads', 'Daugavpils', 'Jelgava', 'Jūrmala', 'Liepāja', 'Rēzekne', 'Rīga', 'Ventspils'],
        subregions={'Rīga City': ['Riga City Centre', 'Ziepniekkalns', 'Purvciems', 'Imanta'], 'Liepāja City': ['Liepāja City'], 'Daugavpils City': ['Daugavpils City'], 'Jelgava City': ['Jelgava City'], 'Valmiera City': ['Valmiera City'], 'Jūrmala City': ['Jūrmala City'], 'Rēzekne City': ['Rēzekne City'], 'Cēsis Municipality': ['Cēsis', 'Valmiera']},
    ),
    'LY': CountryLocationConfig(
        region_label='District',
        subregion_label='Municipality',
        regions=['Tripoli', 'Benghazi', 'Misrata', 'Banghāzī', 'Al Buţnān', 'Darnah', 'Ghāt', 'Al Jabal al Akhḑar', 'Al Jabal al Gharbī', 'Al Jafārah', 'Al Jufrah', 'Al Kufrah', 'Al Marqab', 'Mişrātah', 'Al Marj', 'Murzuq', 'Nālūt', 'An Nuqāţ al Khams', 'Sabhā', 'Surt', 'Ţarābulus', 'Al Wāḩāt', 'Wādī al Ḩayāt', 'Wādī ash Shāţi’', 'Az Zāwiyah'],
        subregions={},
    ),
    'MA': CountryLocationConfig(
        region_label='Region',
        subregion_label='Province',
        regions=['Casablanca-Settat', 'Rabat-Salé-Kénitra', 'Marrakech-Safi', 'Tanger-Tétouan-Al Hoceïma', "L'Oriental", 'Fès-Meknès', 'Béni Mellal-Khénifra', 'Drâa-Tafilalet', 'Souss-Massa', 'Guelmim-Oued Noun (EH-partial)', 'Laâyoune-Sakia El Hamra (EH-partial)', 'Dakhla-Oued Ed-Dahab (EH)'],
        subregions={},
    ),
    'MC': CountryLocationConfig(
        region_label='Ward',
        subregion_label='Quarter',
        regions=['Fontvieille', 'La Condamine', 'Larvotto', 'Les Moneghetti', 'Monaco-Ville', 'Monte Carlo', 'Moneghetti', 'La Colle', 'La Gare', 'Jardin Exotique', 'Malbousquet', 'Moulins', 'Port-Hercule', 'Sainte-Dévote', 'La Source', 'Spélugues', 'Saint-Roman', 'Vallon de la Rousse'],
        subregions={'Monte Carlo': ['Monte Carlo'], 'Monaco-Ville': ['Monaco City'], 'La Condamine': ['La Condamine Quarter'], 'Larvotto': ['Larvotto Quarter'], 'Fontvieille': ['Fontvieille Quarter']},
    ),
    'MD': CountryLocationConfig(
        region_label='District',
        subregion_label='Locality',
        regions=['Anenii Noi', 'Basarabeasca', 'Briceni', 'Cahul', 'Cantemir', 'Călărași', 'Căușeni', 'Cimișlia', 'Criuleni', 'Dondușeni', 'Drochia', 'Dubăsari', 'Edineț', 'Fălești', 'Florești', 'Glodeni', 'Hîncești', 'Ialoveni', 'Leova', 'Nisporeni', 'Ocnița', 'Orhei', 'Rezina', 'Rîșcani', 'Sîngerei', 'Soroca', 'Strășeni', 'Șoldănești', 'Ștefan Vodă', 'Taraclia', 'Telenești', 'Ungheni', 'Chișinău Municipality', 'Bălți Municipality', 'Comrat Municipality', 'Tiraspol Municipality', 'Bălți', 'Bender [Tighina]', 'Chișinău', 'Găgăuzia, Unitatea teritorială autonomă (UTAG)', 'Stînga Nistrului, unitatea teritorială din'],
        subregions={'Chișinău Municipality': ['Chișinău City', 'Cricova', 'Stăuceni'], 'Bălți Municipality': ['Bălți City'], 'Orhei': ['Orhei City', 'Rezina City'], 'Ungheni': ['Ungheni City'], 'Soroca': ['Soroca City', 'Floriești'], 'Cahul': ['Cahul City', 'Leova City']},
    ),
    'ME': CountryLocationConfig(
        region_label='Municipality',
        subregion_label='Settlement',
        regions=['Andrijevica', 'Bar', 'Berane', 'Bijelo Polje', 'Budva', 'Cetinje', 'Danilovgrad', 'Gusinje', 'Herceg Novi', 'Kolašin', 'Kotor', 'Mojkovac', 'Nikšić', 'Petnjica', 'Plav', 'Pljevlja', 'Plužine', 'Podgorica', 'Rožaje', 'Šavnik', 'Tivat', 'Tuzi', 'Ulcinj', 'Žabljak', 'Zeta'],
        subregions={'Podgorica': ['Podgorica City', 'Golubovci', 'Tuzi'], 'Nikšić': ['Nikšić City', 'Šavnik'], 'Bar': ['Bar City', 'Ulcinj City'], 'Budva': ['Budva City', 'Petrovac'], 'Kotor': ['Kotor City', 'Tivat City'], 'Herceg Novi': ['Herceg Novi City']},
    ),
    'MF': CountryLocationConfig(
        region_label='Territory',
        subregion_label='Locality',
        regions=['Saint Martin (French part)'],
        subregions={},
    ),
    'MG': CountryLocationConfig(
        region_label='Region',
        subregion_label='District',
        regions=['Analamanga', 'Atsinanana', 'Boeny', 'Toamasina', 'Antsiranana', 'Fianarantsoa', 'Mahajanga', 'Antananarivo', 'Toliara'],
        subregions={},
    ),
    'MH': CountryLocationConfig(
        region_label='Chain',
        subregion_label='Atoll',
        regions=['Ratak Chain', 'Ralik Chain'],
        subregions={'Ratak Chain': ['Majuro', 'Arno', 'Aur', 'Likiep', 'Maloelap', 'Mili', 'Wotje'], 'Ralik Chain': ['Kwajalein', 'Ailinglaplap', 'Ebon', 'Jaluit', 'Namorik', 'Namu', 'Rongelap', 'Wotho', 'Ujae']},
    ),
    'MK': CountryLocationConfig(
        region_label='Region',
        subregion_label='Municipality',
        regions=['Skopje Region', 'Pelagonia Region', 'Vardar Region', 'Southeast Region', 'East Region', 'Northeast Region', 'Southwest Region', 'Polog Region', 'Veles', 'Gradsko', 'Demir Kapija', 'Kavadarci', 'Lozovo', 'Negotino', 'Rosoman', 'Sveti Nikole', 'Čaška', 'Berovo', 'Vinica', 'Delčevo', 'Zrnovci', 'Karbinci', 'Kočani', 'Makedonska Kamenica', 'Pehčevo', 'Probištip', 'Češinovo-Obleševo', 'Štip', 'Vevčani', 'Debar', 'Debrca', 'Kičevo', 'Makedonski Brod', 'Ohrid', 'Plasnica', 'Struga', 'Centar Župa', 'Bogdanci', 'Bosilovo', 'Valandovo', 'Vasilevo', 'Gevgelija', 'Dojran', 'Konče', 'Novo Selo', 'Radoviš', 'Strumica', 'Bitola', 'Demir Hisar', 'Dolneni', 'Krivogaštani', 'Kruševo', 'Mogila', 'Novaci', 'Prilep', 'Resen', 'Bogovinje', 'Brvenica', 'Vrapčište', 'Gostivar', 'Želino', 'Jegunovce', 'Mavrovo i Rostuše', 'Tearce', 'Tetovo', 'Kratovo', 'Kriva Palanka', 'Kumanovo', 'Lipkovo', 'Rankovce', 'Staro Nagoričane', 'Aerodrom †', 'Aračinovo', 'Butel †', 'Gazi Baba †', 'Gjorče Petrov †', 'Zelenikovo', 'Ilinden', 'Karpoš †', 'Kisela Voda †', 'Petrovec', 'Saraj †', 'Sopište', 'Studeničani', 'Centar †', 'Čair †', 'Čučer-Sandevo', 'Šuto Orizari †'],
        subregions={'Skopje Region': ['Skopje City', 'Čair', 'Gazi Baba', 'Kisela Voda', 'Karpoš'], 'Pelagonia Region': ['Bitola', 'Herakleia', 'Prilepsko'], 'Polog Region': ['Tetovo', 'Gostivar', 'Jegunovce'], 'Southwest Region': ['Ohrid', 'Struga', 'Resen'], 'East Region': ['Štip', 'Radoviš', 'Kočani'], 'Vardar Region': ['Veles', 'Kavadarci', 'Negotino']},
    ),
    'ML': CountryLocationConfig(
        region_label='Region',
        subregion_label='Cercle',
        regions=['Bamako', 'Sikasso', 'Koulikoro', 'Kayes', 'Taoudénit', 'Ségou', 'Mopti', 'Tombouctou', 'Gao', 'Kidal', 'Ménaka'],
        subregions={},
    ),
    'MM': CountryLocationConfig(
        region_label='State/Region',
        subregion_label='Township',
        regions=['Ayeyarwady Region', 'Bago Region', 'Chin State', 'Kachin State', 'Kayah State', 'Kayin State', 'Magway Region', 'Mandalay Region', 'Mon State', 'Naypyidaw Union Territory', 'Rakhine State', 'Sagaing Region', 'Shan State', 'Tanintharyi Region', 'Yangon Region', 'Sagaing', 'Bago', 'Magway', 'Mandalay', 'Tanintharyi', 'Yangon', 'Ayeyarwady', 'Kachin', 'Kayah', 'Kayin', 'Chin', 'Mon', 'Rakhine', 'Shan', 'Nay Pyi Taw'],
        subregions={'Yangon Region': ['Yangon City', 'Insein', 'Thingangyun', 'Dagon', 'Hlaing'], 'Mandalay Region': ['Mandalay City', 'Amarapura', 'Sagaing', 'Kyaukse'], 'Bago Region': ['Bago City', 'Toungoo', 'Nyaunglebin'], 'Magway Region': ['Magway City', 'Pakokku', 'Yenangyaung'], 'Sagaing Region': ['Sagaing City', 'Monywa', 'Shwebo'], 'Shan State': ['Taunggyi', 'Lashio', 'Kengtung'], 'Ayeyarwady Region': ['Pathein', 'Hinthada', 'Myaungmya'], 'Naypyidaw Union Territory': ['Naypyidaw City']},
    ),
    'MN': CountryLocationConfig(
        region_label='Province',
        subregion_label='District',
        regions=['Arkhangai', 'Bayan-Ölgii', 'Bayankhongor', 'Bulgan', 'Darkhan-Uul', 'Dornod', 'Dornogovi', 'Dundgovi', 'Govi-Altai', 'Govisümber', 'Khentii', 'Khovd', 'Khövsgöl', 'Orkhon', 'Övörkhangai', 'Selenge', 'Sükhbaatar', 'Töv', 'Ulaanbaatar', 'Uvs', 'Zavkhan', 'Orhon', 'Darhan uul', 'Hentiy', 'Hövsgöl', 'Hovd', 'Sühbaatar', 'Ömnögovĭ', 'Övörhangay', 'Dzavhan', 'Govĭ-Sümber', 'Govĭ-Altay', 'Bayanhongor', 'Bayan-Ölgiy', 'Arhangay'],
        subregions={'Ulaanbaatar': ['Bayangol', 'Bayanzürkh', 'Chingeltei', 'Songino Khairkhan', 'Sükhbaatar'], 'Darkhan-Uul': ['Darkhan City', 'Khongor'], 'Orkhon': ['Erdenet City'], 'Selenge': ['Sükhbaatar City', 'Zuunbulag'], 'Töv': ['Zuunmod', 'Lün'], 'Khövsgöl': ['Mörön', 'Khatgal']},
    ),
    'MO': CountryLocationConfig(
        region_label='Territory',
        subregion_label='Locality',
        regions=['Macao'],
        subregions={},
    ),
    'MP': CountryLocationConfig(
        region_label='Territory',
        subregion_label='Locality',
        regions=['Northern Mariana Islands'],
        subregions={},
    ),
    'MQ': CountryLocationConfig(
        region_label='Territory',
        subregion_label='Locality',
        regions=['Martinique'],
        subregions={},
    ),
    'MR': CountryLocationConfig(
        region_label='Region',
        subregion_label='Department',
        regions=['Nouakchott', 'Dakhlet Nouadhibou', 'Trarza', 'Hodh ech Chargui', 'Hodh el Gharbi', 'Assaba', 'Gorgol', 'Brakna', 'Adrar', 'Tagant', 'Guidimaka', 'Tiris Zemmour', 'Inchiri', 'Nouakchott Ouest', 'Nouakchott Nord', 'Nouakchott Sud'],
        subregions={},
    ),
    'MS': CountryLocationConfig(
        region_label='Territory',
        subregion_label='Locality',
        regions=['Montserrat'],
        subregions={},
    ),
    'MT': CountryLocationConfig(
        region_label='Region',
        subregion_label='Locality',
        regions=['Gozo and Comino', 'Northern Harbour', 'Northern', 'South Eastern', 'Southern Harbour', 'Western', 'Attard', 'Balzan', 'Birgu', 'Birkirkara', 'Birżebbuġa', 'Bormla', 'Dingli', 'Fgura', 'Floriana', 'Fontana', 'Gudja', 'Gżira', 'Għajnsielem', 'Għarb', 'Għargħur', 'Għasri', 'Għaxaq', 'Ħamrun', 'Iklin', 'Isla', 'Kalkara', 'Kerċem', 'Kirkop', 'Lija', 'Luqa', 'Marsa', 'Marsaskala', 'Marsaxlokk', 'Mdina', 'Mellieħa', 'Mġarr', 'Mosta', 'Mqabba', 'Msida', 'Mtarfa', 'Munxar', 'Nadur', 'Naxxar', 'Paola', 'Pembroke', 'Pietà', 'Qala', 'Qormi', 'Qrendi', 'Rabat Gozo', 'Rabat Malta', 'Safi', "Saint Julian's", 'Saint John', 'Saint Lawrence', "Saint Paul's Bay", 'Sannat', "Saint Lucia's", 'Santa Venera', 'Siġġiewi', 'Sliema', 'Swieqi', "Ta' Xbiex", 'Tarxien', 'Valletta', 'Xagħra', 'Xewkija', 'Xgħajra', 'Żabbar', 'Żebbuġ Gozo', 'Żebbuġ Malta', 'Żejtun', 'Żurrieq'],
        subregions={'Northern Harbour': ['Valletta', 'Floriana', 'Sliema', "St. Julian's", 'Gżira', 'Msida'], 'Southern Harbour': ['Birgu', 'Cospicua', 'Kalkara', 'Senglea', 'Xgħajra'], 'Northern': ['Mellieħa', 'Mġarr', 'Mosta', 'Naxxar', 'San Ġwann'], 'Western': ['Attard', 'Balzan', 'Iklin', 'Lija', 'Mdina', 'Rabat'], 'South Eastern': ['Birżebbuġa', 'Marsaxlokk', 'Qrendi', 'Żurrieq'], 'Gozo and Comino': ['Victoria (Rabat)', 'Marsalforn', 'Xlendi', 'Nadur']},
    ),
    'MU': CountryLocationConfig(
        region_label='District',
        subregion_label='Village Council',
        regions=['Port Louis', 'Plaines Wilhems', 'Pamplemousses', 'Agalega Islands', 'Black River', 'Cargados Carajos Shoals', 'Flacq', 'Grand Port', 'Moka', 'Rodrigues Island', 'Rivière du Rempart', 'Savanne'],
        subregions={},
    ),
    'MV': CountryLocationConfig(
        region_label='Atoll',
        subregion_label='Island',
        regions=['Haa Alif Atoll', 'Haa Dhaalu Atoll', 'Shaviyani Atoll', 'Noonu Atoll', 'Raa Atoll', 'Baa Atoll', 'Lhaviyani Atoll', 'Kaafu Atoll', 'Alifu Alifu Atoll', 'Alifu Dhaalu Atoll', 'Vaavu Atoll', 'Meemu Atoll', 'Faafu Atoll', 'Dhaalu Atoll', 'Thaa Atoll', 'Laamu Atoll', 'Gaafu Alifu Atoll', 'Gaafu Dhaalu Atoll', 'Gnaviyani Atoll', 'Seenu Atoll', 'Malé City', 'South Ari Atoll', 'Addu City', 'North Ari Atoll', 'Faadhippolhu', 'Felidhu Atoll', 'Hahdhunmathi', 'North Thiladhunmathi', 'Kolhumadulu', 'Mulaku Atoll', 'North Maalhosmadulu', 'North Nilandhe Atoll', 'South Nilandhe Atoll', 'South Maalhosmadulu', 'South Thiladhunmathi', 'North Miladhunmadulu', 'South Miladhunmadulu', 'Male Atoll', 'North Huvadhu Atoll', 'South Huvadhu Atoll', 'Fuvammulah', 'Male'],
        subregions={'Malé City': ['Malé', 'Hulhumalé', 'Villingili'], 'Kaafu Atoll': ['Hulhulé', 'Maafushi', 'Guraidhoo'], 'Seenu Atoll': ['Addu City', 'Hithadhoo', 'Fuvahmulah'], 'Alifu Alifu Atoll': ['Rasdhoo', 'Ukulhas', 'Bodufolhudhoo'], 'Gaafu Dhaalu Atoll': ['Thinadhoo', 'Madaveli']},
    ),
    'MW': CountryLocationConfig(
        region_label='Region',
        subregion_label='District',
        regions=['Central', 'Northern', 'Southern', 'Central Region', 'Northern Region', 'Southern Region'],
        subregions={},
    ),
    'MX': CountryLocationConfig(
        region_label='State',
        subregion_label='Municipality',
        regions=['Aguascalientes', 'Baja California', 'Baja California Sur', 'Campeche', 'Chiapas', 'Chihuahua', 'Coahuila', 'Colima', 'Durango', 'Guanajuato', 'Guerrero', 'Hidalgo', 'Jalisco', 'Mexico City', 'Mexico State', 'Michoacán', 'Morelos', 'Nayarit', 'Nuevo León', 'Oaxaca', 'Puebla', 'Querétaro', 'Quintana Roo', 'San Luis Potosí', 'Sinaloa', 'Sonora', 'Tabasco', 'Tamaulipas', 'Tlaxcala', 'Veracruz', 'Yucatán', 'Zacatecas', 'Ciudad de México', 'Coahuila de Zaragoza', 'México', 'Michoacán de Ocampo', 'Veracruz de Ignacio de la Llave'],
        subregions={'Mexico City': ['Benito Juárez', 'Cuauhtémoc', 'Iztapalapa', 'Gustavo A. Madero', 'Tlalpan'], 'Jalisco': ['Guadalajara', 'Zapopan', 'Tlaquepaque', 'Tonalá', 'Tlajomulco'], 'Nuevo León': ['Monterrey', 'Guadalupe', 'San Nicolás', 'Apodaca', 'General Escobedo'], 'Puebla': ['Puebla City', 'Tehuacán', 'San Martín Texmelucan'], 'Guanajuato': ['León', 'Irapuato', 'Celaya', 'Guanajuato City', 'Salamanca'], 'Veracruz': ['Veracruz City', 'Xalapa', 'Coatzacoalcos', 'Córdoba'], 'Oaxaca': ['Oaxaca City', 'Salina Cruz', 'Juchitán'], 'Chihuahua': ['Juárez', 'Chihuahua City', 'Delicias', 'Cuauhtémoc']},
    ),
    'MY': CountryLocationConfig(
        region_label='State',
        subregion_label='District',
        regions=['Johor', 'Kedah', 'Kelantan', 'Kuala Lumpur', 'Labuan', 'Melaka', 'Negeri Sembilan', 'Pahang', 'Penang', 'Perak', 'Perlis', 'Putrajaya', 'Sabah', 'Sarawak', 'Selangor', 'Terengganu', 'Pulau Pinang', 'Wilayah Persekutuan Kuala Lumpur', 'Wilayah Persekutuan Labuan', 'Wilayah Persekutuan Putrajaya'],
        subregions={'Kuala Lumpur': ['Kuala Lumpur City'], 'Selangor': ['Shah Alam', 'Petaling Jaya', 'Subang Jaya', 'Klang', 'Ampang'], 'Johor': ['Johor Bahru', 'Batu Pahat', 'Muar', 'Kluang', 'Segamat'], 'Perak': ['Ipoh', 'Taiping', 'Teluk Intan', 'Manjung'], 'Penang': ['Georgetown', 'Butterworth', 'Seberang Perai'], 'Sabah': ['Kota Kinabalu', 'Sandakan', 'Tawau', 'Lahad Datu'], 'Sarawak': ['Kuching', 'Miri', 'Sibu', 'Bintulu'], 'Pahang': ['Kuantan', 'Temerloh', 'Bentong', 'Raub']},
    ),
    'MZ': CountryLocationConfig(
        region_label='Province',
        subregion_label='District',
        regions=['Maputo', 'Sofala', 'Nampula', 'Niassa', 'Manica', 'Gaza', 'Inhambane', 'Cabo Delgado', 'Zambézia', 'Tete'],
        subregions={},
    ),
    'NA': CountryLocationConfig(
        region_label='Region',
        subregion_label='Constituency',
        regions=['Khomas', 'Erongo', 'Oshana', 'Zambezi', 'Hardap', '//Karas', 'Kavango East', 'Kunene', 'Kavango West', 'Otjozondjupa', 'Omaheke', 'Omusati', 'Oshikoto', 'Ohangwena'],
        subregions={},
    ),
    'NC': CountryLocationConfig(
        region_label='Territory',
        subregion_label='Locality',
        regions=['New Caledonia'],
        subregions={},
    ),
    'NE': CountryLocationConfig(
        region_label='Region',
        subregion_label='Department',
        regions=['Niamey', 'Zinder', 'Maradi', 'Agadez', 'Diffa', 'Dosso', 'Tahoua', 'Tillabéri'],
        subregions={},
    ),
    'NF': CountryLocationConfig(
        region_label='Territory',
        subregion_label='Locality',
        regions=['Norfolk Island'],
        subregions={},
    ),
    'NG': CountryLocationConfig(
        region_label='State',
        subregion_label='LGA',
        regions=['Abia', 'Adamawa', 'Akwa Ibom', 'Anambra', 'Bauchi', 'Bayelsa', 'Benue', 'Borno', 'Cross River', 'Delta', 'Ebonyi', 'Edo', 'Ekiti', 'Enugu', 'Federal Capital Territory', 'Gombe', 'Imo', 'Jigawa', 'Kaduna', 'Kano', 'Katsina', 'Kebbi', 'Kogi', 'Kwara', 'Lagos', 'Nasarawa', 'Niger', 'Ogun', 'Ondo', 'Osun', 'Oyo', 'Plateau', 'Rivers', 'Sokoto', 'Taraba', 'Yobe', 'Zamfara', 'Abuja Federal Capital Territory'],
        subregions={'Abia': ['Aba North', 'Aba South', 'Arochukwu', 'Bende', 'Ikwuano', 'Isiala Ngwa North', 'Isiala Ngwa South', 'Isuikwuato', 'Obi Ngwa', 'Ohafia', 'Osisioma', 'Ugwunagbo', 'Ukwa East', 'Ukwa West', 'Umuahia North', 'Umuahia South', 'Umu Nneochi'], 'Adamawa': ['Demsa', 'Fufure', 'Ganye', 'Girei', 'Gombi', 'Guyuk', 'Hong', 'Jada', 'Lamurde', 'Madagali', 'Maiha', 'Mayo Belwa', 'Michika', 'Mubi North', 'Mubi South', 'Numan', 'Shelleng', 'Song', 'Toungo', 'Yola North', 'Yola South'], 'Akwa Ibom': ['Abak', 'Eastern Obolo', 'Eket', 'Esit Eket', 'Essien Udim', 'Etim Ekpo', 'Etinan', 'Ibeno', 'Ibesikpo Asutan', 'Ibiono Ibom', 'Ika', 'Ikono', 'Ikot Abasi', 'Ikot Ekpene', 'Ini', 'Itu', 'Mbo', 'Mkpat Enin', 'Nsit Atai', 'Nsit Ibom', 'Nsit Ubium', 'Obot Akara', 'Okobo', 'Onna', 'Oron', 'Oruk Anam', 'Udung Uko', 'Ukanafun', 'Uruan', 'Urue-Offong/Oruko', 'Uyo'], 'Anambra': ['Aguata', 'Anambra East', 'Anambra West', 'Anaocha', 'Awka North', 'Awka South', 'Ayamelum', 'Dunukofia', 'Ekwusigo', 'Idemili North', 'Idemili South', 'Ihiala', 'Njikoka', 'Nnewi North', 'Nnewi South', 'Ogbaru', 'Onitsha North', 'Onitsha South', 'Orumba North', 'Orumba South', 'Oyi'], 'Bauchi': ['Alkaleri', 'Bauchi', 'Bogoro', 'Damban', 'Darazo', 'Dass', 'Gamawa', 'Ganjuwa', 'Giade', 'Itas/Gadau', "Jama'are", 'Katagum', 'Kirfi', 'Misau', 'Ningi', 'Shira', 'Tafawa Balewa', 'Toro', 'Warji', 'Zaki'], 'Bayelsa': ['Brass', 'Ekeremor', 'Kolokuma/Opokuma', 'Nembe', 'Ogbia', 'Sagbama', 'Southern Ijaw', 'Yenagoa'], 'Benue': ['Ado', 'Agatu', 'Apa', 'Buruku', 'Gboko', 'Guma', 'Gwer East', 'Gwer West', 'Katsina-Ala', 'Konshisha', 'Kwande', 'Logo', 'Makurdi', 'Obi', 'Ogbadibo', 'Ohimini', 'Oju', 'Okpokwu', 'Otukpo', 'Tarka', 'Ukum', 'Ushongo', 'Vandeikya'], 'Borno': ['Abadam', 'Askira/Uba', 'Bama', 'Bayo', 'Biu', 'Chibok', 'Damboa', 'Dikwa', 'Gubio', 'Guzamala', 'Gwoza', 'Hawul', 'Jere', 'Kaga', 'Kala/Balge', 'Konduga', 'Kukawa', 'Kwaya Kusar', 'Mafa', 'Magumeri', 'Maiduguri', 'Marte', 'Mobbar', 'Monguno', 'Ngala', 'Nganzai', 'Shani'], 'Cross River': ['Abi', 'Akamkpa', 'Akpabuyo', 'Bakassi', 'Bekwarra', 'Biase', 'Boki', 'Calabar Municipal', 'Calabar South', 'Etung', 'Ikom', 'Obanliku', 'Obubra', 'Obudu', 'Odukpani', 'Ogoja', 'Yakurr', 'Yala'], 'Delta': ['Aniocha North', 'Aniocha South', 'Bomadi', 'Burutu', 'Ethiope East', 'Ethiope West', 'Ika North East', 'Ika South', 'Isoko North', 'Isoko South', 'Ndokwa East', 'Ndokwa West', 'Okpe', 'Oshimili North', 'Oshimili South', 'Patani', 'Sapele', 'Udu', 'Ughelli North', 'Ughelli South', 'Ukwuani', 'Uvwie', 'Warri North', 'Warri South', 'Warri South West'], 'Ebonyi': ['Abakaliki', 'Afikpo North', 'Afikpo South', 'Ebonyi', 'Ezza North', 'Ezza South', 'Ikwo', 'Ishielu', 'Ivo', 'Izzi', 'Ohaozara', 'Ohaukwu', 'Onicha'], 'Edo': ['Akoko-Edo', 'Egor', 'Esan Central', 'Esan North-East', 'Esan South-East', 'Esan West', 'Etsako Central', 'Etsako East', 'Etsako West', 'Igueben', 'Ikpoba Okha', 'Orhionmwon', 'Oredo', 'Ovia North-East', 'Ovia South-West', 'Owan East', 'Owan West', 'Uhunmwonde'], 'Ekiti': ['Ado Ekiti', 'Efon', 'Ekiti East', 'Ekiti South-West', 'Ekiti West', 'Emure', 'Gbonyin', 'Ido Osi', 'Ijero', 'Ikere', 'Ikole', 'Ilejemeje', 'Irepodun/Ifelodun', 'Ise/Orun', 'Moba', 'Oye'], 'Enugu': ['Aninri', 'Awgu', 'Enugu East', 'Enugu North', 'Enugu South', 'Ezeagu', 'Igbo Etiti', 'Igbo Eze North', 'Igbo Eze South', 'Isi Uzo', 'Nkanu East', 'Nkanu West', 'Nsukka', 'Oji River', 'Udenu', 'Udi', 'Uzo Uwani'], 'Federal Capital Territory': ['Abaji', 'Abuja Municipal', 'Bwari', 'Gwagwalada', 'Kuje', 'Kwali'], 'Gombe': ['Akko', 'Balanga', 'Billiri', 'Dukku', 'Funakaye', 'Gombe', 'Kaltungo', 'Kwami', 'Nafada', 'Shongom', 'Yamaltu/Deba'], 'Imo': ['Aboh Mbaise', 'Ahiazu Mbaise', 'Ehime Mbano', 'Ezinihitte', 'Ideato North', 'Ideato South', 'Ihitte/Uboma', 'Ikeduru', 'Isiala Mbano', 'Isu', 'Mbaitoli', 'Ngor Okpala', 'Njaba', 'Nkwerre', 'Nwangele', 'Obowo', 'Oguta', 'Ohaji/Egbema', 'Okigwe', 'Onuimo', 'Orlu', 'Orsu', 'Oru East', 'Oru West', 'Owerri Municipal', 'Owerri North', 'Owerri West'], 'Jigawa': ['Auyo', 'Babura', 'Biriniwa', 'Birnin Kudu', 'Buji', 'Dutse', 'Gagarawa', 'Garki', 'Gumel', 'Guri', 'Gwaram', 'Gwiwa', 'Hadejia', 'Jahun', 'Kafin Hausa', 'Kaugama', 'Kazaure', 'Kiri Kasama', 'Kiyawa', 'Maigatari', 'Malam Madori', 'Miga', 'Ringim', 'Roni', 'Sule Tankarkar', 'Taura', 'Yankwashi'], 'Kaduna': ['Birnin Gwari', 'Chikun', 'Giwa', 'Igabi', 'Ikara', 'Jaba', "Jema'a", 'Kachia', 'Kaduna North', 'Kaduna South', 'Kagarko', 'Kajuru', 'Kaura', 'Kauru', 'Kubau', 'Kudan', 'Lere', 'Makarfi', 'Sabon Gari', 'Sanga', 'Soba', 'Zangon Kataf', 'Zaria'], 'Kano': ['Ajingi', 'Albasu', 'Bagwai', 'Bebeji', 'Bichi', 'Bunkure', 'Dala', 'Dambatta', 'Dawakin Kudu', 'Dawakin Tofa', 'Doguwa', 'Fagge', 'Gabasawa', 'Garko', 'Garun Mallam', 'Gaya', 'Gezawa', 'Gwale', 'Gwarzo', 'Kabo', 'Kano Municipal', 'Karaye', 'Kibiya', 'Kiru', 'Kumbotso', 'Kunchi', 'Kura', 'Madobi', 'Makoda', 'Minjibir', 'Nasarawa', 'Rano', 'Rimin Gado', 'Rogo', 'Shanono', 'Sumaila', 'Takai', 'Tarauni', 'Tofa', 'Tsanyawa', 'Tudun Wada', 'Ungogo', 'Warawa', 'Wudil'], 'Katsina': ['Bakori', 'Batagarawa', 'Batsari', 'Baure', 'Bindawa', 'Charanchi', 'Dandume', 'Danja', 'Dan Musa', 'Daura', 'Dutsi', 'Dutsin Ma', 'Faskari', 'Funtua', 'Ingawa', 'Jibia', 'Kafur', 'Kaita', 'Kankara', 'Kankia', 'Katsina', 'Kurfi', 'Kusada', "Mai'Adua", 'Malumfashi', 'Mani', 'Mashi', 'Matazu', 'Musawa', 'Rimi', 'Sabuwa', 'Safana', 'Sandamu', 'Zango'], 'Kebbi': ['Aleiro', 'Arewa Dandi', 'Argungu', 'Augie', 'Bagudo', 'Birnin Kebbi', 'Bunza', 'Dandi', 'Fakai', 'Gwandu', 'Jega', 'Kalgo', 'Koko/Besse', 'Maiyama', 'Ngaski', 'Sakaba', 'Shanga', 'Suru', 'Wasagu/Danko', 'Yauri', 'Zuru'], 'Kogi': ['Adavi', 'Ajaokuta', 'Ankpa', 'Bassa', 'Dekina', 'Ibaji', 'Idah', 'Igalamela Odolu', 'Ijumu', 'Kabba/Bunu', 'Kogi', 'Lokoja', 'Mopa Muro', 'Ofu', 'Ogori/Magongo', 'Okehi', 'Okene', 'Olamaboro', 'Omala', 'Yagba East', 'Yagba West'], 'Kwara': ['Asa', 'Baruten', 'Edu', 'Ekiti', 'Ifelodun', 'Ilorin East', 'Ilorin South', 'Ilorin West', 'Irepodun', 'Isin', 'Kaiama', 'Moro', 'Offa', 'Oke Ero', 'Oyun', 'Pategi'], 'Lagos': ['Agege', 'Ajeromi-Ifelodun', 'Alimosho', 'Amuwo-Odofin', 'Apapa', 'Badagry', 'Epe', 'Eti Osa', 'Ibeju-Lekki', 'Ifako-Ijaiye', 'Ikeja', 'Ikorodu', 'Kosofe', 'Lagos Island', 'Lagos Mainland', 'Mushin', 'Ojo', 'Oshodi-Isolo', 'Shomolu', 'Surulere'], 'Nasarawa': ['Akwanga', 'Awe', 'Doma', 'Karu', 'Keana', 'Keffi', 'Kokona', 'Lafia', 'Nasarawa', 'Nasarawa Egon', 'Obi', 'Toto', 'Wamba'], 'Niger': ['Agaie', 'Agwara', 'Bida', 'Borgu', 'Bosso', 'Chanchaga', 'Edati', 'Gbako', 'Gurara', 'Katcha', 'Kontagora', 'Lapai', 'Lavun', 'Magama', 'Mariga', 'Mashegu', 'Mokwa', 'Moya', 'Paikoro', 'Rafi', 'Rijau', 'Shiroro', 'Suleja', 'Tafa', 'Wushishi'], 'Ogun': ['Abeokuta North', 'Abeokuta South', 'Ado-Odo/Ota', 'Egbado North (Yewa North)', 'Egbado South (Yewa South)', 'Ewekoro', 'Ifo', 'Ijebu East', 'Ijebu North', 'Ijebu North East', 'Ijebu Ode', 'Ikenne', 'Imeko Afon', 'Ipokia', 'Obafemi Owode', 'Odeda', 'Odogbolu', 'Ogun Waterside', 'Remo North', 'Shagamu'], 'Ondo': ['Akoko North-East', 'Akoko North-West', 'Akoko South-East', 'Akoko South-West', 'Akure North', 'Akure South', 'Ese Odo', 'Idanre', 'Ifedore', 'Ilaje', 'Ile Oluji/Okeigbo', 'Irele', 'Odigbo', 'Okitipupa', 'Ondo East', 'Ondo West', 'Ose', 'Owo'], 'Osun': ['Aiyedaade', 'Aiyedire', 'Atakunmosa East', 'Atakunmosa West', 'Boluwaduro', 'Boripe', 'Ede North', 'Ede South', 'Egbedore', 'Ejigbo', 'Ife Central', 'Ife East', 'Ife North', 'Ife South', 'Ifedayo', 'Ifelodun', 'Ila', 'Ilesa East', 'Ilesa West', 'Irepodun', 'Irewole', 'Isokan', 'Iwo', 'Obokun', 'Odo Otin', 'Ola Oluwa', 'Olorunda', 'Oriade', 'Orolu', 'Osogbo'], 'Oyo': ['Afijio', 'Akinyele', 'Atiba', 'Atisbo', 'Egbeda', 'Ibadan North', 'Ibadan North-East', 'Ibadan North-West', 'Ibadan South-East', 'Ibadan South-West', 'Ibarapa Central', 'Ibarapa East', 'Ibarapa North', 'Ido', 'Irepo', 'Iseyin', 'Itesiwaju', 'Iwajowa', 'Kajola', 'Lagelu', 'Ogbomosho North', 'Ogbomosho South', 'Ogo Oluwa', 'Olorunsogo', 'Oluyole', 'Ona Ara', 'Orelope', 'Ori Ire', 'Oyo East', 'Oyo West', 'Saki East', 'Saki West', 'Surulere'], 'Plateau': ['Bokkos', 'Barkin Ladi', 'Bassa', 'Jos East', 'Jos North', 'Jos South', 'Kanam', 'Kanke', 'Langtang North', 'Langtang South', 'Mangu', 'Mikang', 'Pankshin', "Qua'an Pan", 'Riyom', 'Shendam', 'Wase'], 'Rivers': ['Abua/Odual', 'Ahoada East', 'Ahoada West', 'Akuku-Toru', 'Andoni', 'Asari-Toru', 'Bonny', 'Degema', 'Eleme', 'Emuoha', 'Etche', 'Gokana', 'Ikwerre', 'Khana', 'Obio/Akpor', 'Ogba/Egbema/Ndoni', 'Ogu/Bolo', 'Okrika', 'Omuma', 'Opobo/Nkoro', 'Oyigbo', 'Port Harcourt', 'Tai'], 'Sokoto': ['Binji', 'Bodinga', 'Dange Shuni', 'Gada', 'Goronyo', 'Gudu', 'Gwadabawa', 'Illela', 'Isa', 'Kebbe', 'Kware', 'Rabah', 'Sabon Birni', 'Shagari', 'Silame', 'Sokoto North', 'Sokoto South', 'Tambuwal', 'Tangaza', 'Tureta', 'Wamako', 'Wurno', 'Yabo'], 'Taraba': ['Ardo Kola', 'Bali', 'Donga', 'Gashaka', 'Gassol', 'Ibi', 'Jalingo', 'Karim Lamido', 'Kumi', 'Lau', 'Sardauna', 'Takum', 'Ussa', 'Wukari', 'Yorro', 'Zing'], 'Yobe': ['Bade', 'Bursari', 'Damaturu', 'Fika', 'Fune', 'Geidam', 'Gujba', 'Gulani', 'Jakusko', 'Karasuwa', 'Machina', 'Nangere', 'Nguru', 'Potiskum', 'Tarmuwa', 'Yunusari', 'Yusufari'], 'Zamfara': ['Anka', 'Bakura', 'Birnin Magaji/Kiyaw', 'Bukkuyum', 'Bungudu', 'Gummi', 'Gusau', 'Kaura Namoda', 'Maradun', 'Maru', 'Shinkafi', 'Talata Mafara', 'Tsafe', 'Zurmi']},
    ),
    'NI': CountryLocationConfig(
        region_label='Department',
        subregion_label='Municipality',
        regions=['Boaco', 'Carazo', 'Chinandega', 'Chontales', 'Estelí', 'Granada', 'Jinotega', 'León', 'Madriz', 'Managua', 'Masaya', 'Matagalpa', 'Nueva Segovia', 'Río San Juan', 'Rivas', 'North Caribbean Coast', 'South Caribbean Coast', 'Costa Caribe Norte', 'Costa Caribe Sur'],
        subregions={'Managua': ['Managua City', 'Tipitapa', 'Ciudad Sandino', 'Mateare'], 'León': ['León City', 'Chichigalpa', 'Chinandega City', 'El Viejo'], 'Masaya': ['Masaya City', 'Nindirí', 'Jinotepe'], 'Granada': ['Granada City', 'Nandaime'], 'Estelí': ['Estelí City', 'Condega', 'La Trinidad']},
    ),
    'NL': CountryLocationConfig(
        region_label='Province',
        subregion_label='Municipality',
        regions=['North Holland', 'South Holland', 'Utrecht', 'Aruba', 'Bonaire', 'Saba', 'Sint Eustatius', 'Curaçao', 'Drenthe', 'Flevoland', 'Fryslân', 'Gelderland', 'Groningen', 'Limburg', 'Noord-Brabant', 'Noord-Holland', 'Overijssel', 'Sint Maarten', 'Zeeland', 'Zuid-Holland'],
        subregions={},
    ),
    'NO': CountryLocationConfig(
        region_label='County',
        subregion_label='Municipality',
        regions=['Agder', 'Innlandet', 'Møre og Romsdal', 'Nordland', 'Oslo', 'Rogaland', 'Troms og Finnmark', 'Trøndelag', 'Vestfold og Telemark', 'Vestland', 'Viken', 'Svalbard (Arctic Region)', 'Jan Mayen (Arctic Region)', 'Trööndelage', 'Romssa ja Finnmárkku'],
        subregions={'Oslo': ['Oslo City'], 'Viken': ['Bærum', 'Lillestrøm', 'Fredrikstad', 'Sarpsborg', 'Drammen'], 'Vestland': ['Bergen', 'Fjord', 'Alver', 'Bjørnafjorden'], 'Rogaland': ['Stavanger', 'Sandnes', 'Sola', 'Klepp'], 'Trøndelag': ['Trondheim', 'Stjørdal', 'Steinkjer', 'Melhus'], 'Innlandet': ['Hamar', 'Gjøvik', 'Lillehammer', 'Ringsaker'], 'Agder': ['Kristiansand', 'Arendal', 'Grimstad', 'Vennesla']},
    ),
    'NP': CountryLocationConfig(
        region_label='Province',
        subregion_label='District',
        regions=['Koshi Province', 'Madhesh Province', 'Bagmati Province', 'Gandaki Province', 'Lumbini Province', 'Karnali Province', 'Sudurpashchim Province', 'Koshi', 'Madhesh', 'Bagmati', 'Gandaki', 'Lumbini', 'Karnali', 'Sudurpashchim'],
        subregions={'Bagmati Province': ['Kathmandu', 'Lalitpur', 'Bhaktapur', 'Chitwan', 'Makwanpur'], 'Koshi Province': ['Sunsari', 'Morang', 'Dhankuta', 'Terhathum', 'Bhojpur'], 'Madhesh Province': ['Saptari', 'Siraha', 'Dhanusha', 'Mahottari', 'Sarlahi'], 'Gandaki Province': ['Kaski', 'Tanahu', 'Syangja', 'Lamjung', 'Gorkha'], 'Lumbini Province': ['Rupandehi', 'Kapilvastu', 'Palpa', 'Arghakhanchi'], 'Karnali Province': ['Surkhet', 'Dailekh', 'Jumla', 'Dolpa'], 'Sudurpashchim Province': ['Kanchanpur', 'Kailali', 'Doti', 'Bajhang']},
    ),
    'NR': CountryLocationConfig(
        region_label='District',
        subregion_label='Locality',
        regions=['Aiwo', 'Anabar', 'Anetan', 'Anibare', 'Baitsi', 'Boe', 'Buada', 'Denigomodu', 'Ewa', 'Ijuw', 'Meneng', 'Nibok', 'Uaboe', 'Yaren'],
        subregions={'Yaren': ['Yaren District'], 'Aiwo': ['Aiwo District'], 'Buada': ['Buada District'], 'Meneng': ['Meneng District'], 'Denigomodu': ['Denigomodu District']},
    ),
    'NU': CountryLocationConfig(
        region_label='Territory',
        subregion_label='Locality',
        regions=['Niue'],
        subregions={},
    ),
    'NZ': CountryLocationConfig(
        region_label='Region',
        subregion_label='District',
        regions=['Auckland', 'Bay of Plenty', 'Canterbury', 'Gisborne', "Hawke's Bay", 'Manawatu-Whanganui', 'Marlborough', 'Nelson', 'Northland', 'Otago', 'Southland', 'Taranaki', 'Tasman', 'Waikato', 'Wellington', 'West Coast', 'Chatham Islands Territory', 'Greater Wellington'],
        subregions={'Auckland': ['Auckland City', 'North Shore City', 'Waitakere City', 'Manukau City'], 'Wellington': ['Wellington City', 'Lower Hutt', 'Upper Hutt', 'Porirua'], 'Canterbury': ['Christchurch City', 'Selwyn', 'Waimakariri'], 'Waikato': ['Hamilton City', 'Thames-Coromandel', 'Waipa'], 'Bay of Plenty': ['Tauranga City', 'Rotorua', 'Whakatāne'], 'Otago': ['Dunedin City', 'Queenstown-Lakes', 'Central Otago'], "Hawke's Bay": ['Napier City', 'Hastings'], 'Manawatu-Whanganui': ['Palmerston North City', 'Manawatu']},
    ),
    'OM': CountryLocationConfig(
        region_label='Governorate',
        subregion_label='District',
        regions=['Ad Dakhiliyah', 'Ad Dhahirah', 'Al Batinah North', 'Al Batinah South', 'Al Buraymi', 'Al Wusta', 'Ash Sharqiyah North', 'Ash Sharqiyah South', 'Dhofar', 'Musandam', 'Muscat', 'Janūb al Bāţinah', 'Shamāl al Bāţinah', 'Masqaţ', 'Janūb ash Sharqīyah', 'Shamāl ash Sharqīyah', 'Az̧ Z̧āhirah', 'Z̧ufār'],
        subregions={'Muscat': ['Muscat City', 'Muttrah', 'Seeb', 'Bausher', 'Al Amerat'], 'Dhofar': ['Salalah', 'Thumrait', 'Mirbat', 'Rakhyut'], 'Al Batinah North': ['Sohar', 'Shinas', 'Liwa'], 'Al Batinah South': ['Rustaq', 'Al Awabi', 'Nakhal'], 'Ad Dakhiliyah': ['Nizwa', 'Bahla', 'Adam', 'Manah'], 'Ash Sharqiyah North': ['Ibra', 'Al Mudaybi', 'Sur']},
    ),
    'PA': CountryLocationConfig(
        region_label='Province',
        subregion_label='District',
        regions=['Bocas del Toro', 'Chiriquí', 'Coclé', 'Colón', 'Darién', 'Emberá-Wounaan', 'Guna Yala', 'Herrera', 'Los Santos', 'Ngäbe-Buglé', 'Panamá', 'Panamá Oeste', 'Veraguas', 'Emberá', 'Naso Tjër Di'],
        subregions={'Panamá': ['Panama City', 'Chepo', 'Balboa', 'San Miguelito'], 'Panamá Oeste': ['La Chorrera', 'Arraiján', 'Capira', 'Chame'], 'Chiriquí': ['David', 'Barú', 'Boquete', 'Bugaba'], 'Coclé': ['Penonomé', 'Aguadulce', 'Natá', 'Olá'], 'Colón': ['Colón City', 'Portobelo', 'Santa Isabel'], 'Herrera': ['Chitré', 'Los Santos City', 'Ocú']},
    ),
    'PE': CountryLocationConfig(
        region_label='Region',
        subregion_label='Province',
        regions=['Amazonas', 'Áncash', 'Apurímac', 'Arequipa', 'Ayacucho', 'Cajamarca', 'Callao', 'Cusco', 'Huancavelica', 'Huánuco', 'Ica', 'Junín', 'La Libertad', 'Lambayeque', 'Lima', 'Loreto', 'Madre de Dios', 'Moquegua', 'Pasco', 'Piura', 'Puno', 'San Martín', 'Tacna', 'Tumbes', 'Ucayali', 'Amarumayu', 'Apurimaq', 'El Callao', 'Hunin', 'Lima hatun llaqta'],
        subregions={'Lima': ['Lima City', 'Callao City', 'Huaral', 'Cañete', 'Huarochirí'], 'Arequipa': ['Arequipa City', 'Camaná', 'Islay', 'Caravelí'], 'La Libertad': ['Trujillo', 'Chepén', 'Pacasmayo', 'Ascope'], 'Piura': ['Piura City', 'Sullana', 'Talara', 'Morropón'], 'Cusco': ['Cusco City', 'Urubamba', 'Calca', 'Anta'], 'Junín': ['Huancayo', 'La Merced', 'Tarma', 'Jauja'], 'Lambayeque': ['Chiclayo', 'Ferreñafe', 'Lambayeque City']},
    ),
    'PF': CountryLocationConfig(
        region_label='Territory',
        subregion_label='Locality',
        regions=['French Polynesia'],
        subregions={},
    ),
    'PG': CountryLocationConfig(
        region_label='Province',
        subregion_label='District',
        regions=['Bougainville', 'Central', 'Chimbu', 'East New Britain', 'East Sepik', 'Eastern Highlands', 'Enga', 'Gulf', 'Hela', 'Jiwaka', 'Madang', 'Manus', 'Milne Bay', 'Morobe', 'National Capital District', 'New Ireland', 'Northern (Oro)', 'Southern Highlands', 'West New Britain', 'West Sepik', 'Western', 'Western Highlands', 'National Capital District (Port Moresby)', 'Northern'],
        subregions={'National Capital District': ['Port Moresby'], 'Morobe': ['Lae', 'Huon Gulf', 'Markham'], 'Western Highlands': ['Mount Hagen', 'Tambul-Nebilyer'], 'East New Britain': ['Rabaul', 'Kokopo', 'Gazelle'], 'East Sepik': ['Wewak', 'Ambunti-Dreikikir'], 'Madang': ['Madang Town', 'Sumkar'], 'Bougainville': ['Arawa', 'Buka', 'Panguna']},
    ),
    'PH': CountryLocationConfig(
        region_label='Region',
        subregion_label='Province',
        regions=['ARMM', 'CAR', 'Caraga', 'MIMAROPA', 'National Capital Region', 'Region I (Ilocos Region)', 'Region II (Cagayan Valley)', 'Region III (Central Luzon)', 'Region IV-A (Calabarzon)', 'Region V (Bicol Region)', 'Region VI (Western Visayas)', 'Region VII (Central Visayas)', 'Region VIII (Eastern Visayas)', 'Region IX (Zamboanga Peninsula)', 'Region X (Northern Mindanao)', 'Region XI (Davao Region)', 'Region XII (SOCCSKSARGEN)', 'Ilocos (Region I)', 'Cagayan Valley (Region II)', 'Central Luzon (Region III)', 'Bicol (Region V)', 'Western Visayas (Region VI)', 'Central Visayas (Region VII)', 'Eastern Visayas (Region VIII)', 'Zamboanga Peninsula (Region IX)', 'Northern Mindanao (Region X)', 'Davao (Region XI)', 'Soccsksargen (Region XII)', 'Caraga (Region XIII)', 'Autonomous Region in Muslim Mindanao (ARMM)', 'Cordillera Administrative Region (CAR)', 'Calabarzon (Region IV-A)', 'Mimaropa (Region IV-B)'],
        subregions={'National Capital Region': ['Manila', 'Quezon City', 'Makati', 'Pasig', 'Taguig'], 'Region IV-A (Calabarzon)': ['Cavite', 'Laguna', 'Batangas', 'Rizal', 'Quezon'], 'Region III (Central Luzon)': ['Bulacan', 'Pampanga', 'Nueva Ecija', 'Tarlac', 'Zambales'], 'Region VII (Central Visayas)': ['Cebu', 'Bohol', 'Negros Oriental', 'Siquijor'], 'Region XI (Davao Region)': ['Davao del Sur', 'Davao del Norte', 'Davao Oriental', 'Davao Occidental'], 'Region VI (Western Visayas)': ['Iloilo', 'Negros Occidental', 'Capiz', 'Aklan', 'Antique'], 'Region X (Northern Mindanao)': ['Misamis Oriental', 'Bukidnon', 'Lanao del Norte']},
    ),
    'PK': CountryLocationConfig(
        region_label='Province',
        subregion_label='District',
        regions=['Azad Jammu and Kashmir', 'Balochistan', 'Gilgit-Baltistan', 'Islamabad Capital Territory', 'Khyber Pakhtunkhwa', 'Punjab', 'Sindh', 'Islamabad'],
        subregions={'Punjab': ['Lahore', 'Faisalabad', 'Rawalpindi', 'Multan', 'Gujranwala', 'Sialkot'], 'Sindh': ['Karachi', 'Hyderabad', 'Sukkur', 'Larkana', 'Nawabshah'], 'Khyber Pakhtunkhwa': ['Peshawar', 'Mardan', 'Abbottabad', 'Swat', 'Dera Ismail Khan'], 'Balochistan': ['Quetta', 'Turbat', 'Khuzdar', 'Hub', 'Gwadar'], 'Islamabad Capital Territory': ['Islamabad City'], 'Azad Jammu and Kashmir': ['Muzaffarabad', 'Mirpur', 'Rawalakot'], 'Gilgit-Baltistan': ['Gilgit', 'Skardu', 'Chilas']},
    ),
    'PL': CountryLocationConfig(
        region_label='Voivodeship',
        subregion_label='County',
        regions=['Greater Poland', 'Holy Cross', 'Kuyavian-Pomeranian', 'Lesser Poland', 'Łódź', 'Lower Silesian', 'Lublin', 'Lubusz', 'Masovian', 'Opole', 'Podlaskie', 'Pomeranian', 'Silesian', 'Subcarpathian', 'Warmian-Masurian', 'West Pomeranian', 'Dolnośląskie', 'Kujawsko-Pomorskie', 'Lubelskie', 'Lubuskie', 'Łódzkie', 'Małopolskie', 'Mazowieckie', 'Opolskie', 'Podkarpackie', 'Pomorskie', 'Śląskie', 'Świętokrzyskie', 'Warmińsko-Mazurskie', 'Wielkopolskie', 'Zachodniopomorskie'],
        subregions={'Masovian': ['Warsaw', 'Radom', 'Płock', 'Siedlce', 'Ostrołęka'], 'Silesian': ['Katowice', 'Sosnowiec', 'Gliwice', 'Bytom', 'Zabrze'], 'Lesser Poland': ['Kraków', 'Tarnów', 'Nowy Sącz', 'Bielsko-Biała'], 'Greater Poland': ['Poznań', 'Kalisz', 'Konin', 'Piła', 'Ostrów Wielkopolski'], 'Lower Silesian': ['Wrocław', 'Wałbrzych', 'Legnica', 'Jelenia Góra'], 'Pomeranian': ['Gdańsk', 'Gdynia', 'Sopot', 'Słupsk'], 'Łódź': ['Łódź City', 'Piotrków Trybunalski', 'Skierniewice'], 'Kuyavian-Pomeranian': ['Bydgoszcz', 'Toruń', 'Włocławek']},
    ),
    'PM': CountryLocationConfig(
        region_label='Territory',
        subregion_label='Locality',
        regions=['Saint Pierre and Miquelon'],
        subregions={},
    ),
    'PN': CountryLocationConfig(
        region_label='Territory',
        subregion_label='Locality',
        regions=['Pitcairn'],
        subregions={},
    ),
    'PR': CountryLocationConfig(
        region_label='Territory',
        subregion_label='Locality',
        regions=['Puerto Rico'],
        subregions={},
    ),
    'PS': CountryLocationConfig(
        region_label='Governorate',
        subregion_label='Municipality',
        regions=['Bethlehem', 'Deir el-Balah', 'Gaza', 'Hebron', 'Jenin', 'Jericho and Al Aghwar', 'Jerusalem', 'Khan Yunis', 'Nablus', 'North Gaza', 'Qalqilya', 'Rafah', 'Ramallah and Al-Bireh', 'Salfit', 'Tubas', 'Tulkarm', 'Ramallah'],
        subregions={'Gaza': ['Gaza City'], 'Jerusalem': ['East Jerusalem'], 'Ramallah and Al-Bireh': ['Ramallah', 'Al-Bireh'], 'Nablus': ['Nablus City'], 'Hebron': ['Hebron City'], 'Jenin': ['Jenin City'], 'Bethlehem': ['Bethlehem City']},
    ),
    'PT': CountryLocationConfig(
        region_label='District',
        subregion_label='Municipality',
        regions=['Lisbon', 'Porto', 'Braga', 'Aveiro', 'Beja', 'Bragança', 'Castelo Branco', 'Coimbra', 'Évora', 'Faro', 'Guarda', 'Leiria', 'Lisboa', 'Portalegre', 'Santarém', 'Setúbal', 'Viana do Castelo', 'Vila Real', 'Viseu', 'Região Autónoma dos Açores', 'Região Autónoma da Madeira'],
        subregions={},
    ),
    'PW': CountryLocationConfig(
        region_label='State',
        subregion_label='Village',
        regions=['Aimeliik', 'Airai', 'Angaur', 'Hatohobei', 'Kayangel', 'Koror', 'Melekeok', 'Ngaraard', 'Ngarchelong', 'Ngardmau', 'Ngatpang', 'Ngchesar', 'Ngeremlengui', 'Ngiwal', 'Peleliu', 'Sonsorol'],
        subregions={'Koror': ['Koror City'], 'Melekeok': ['Ngerulmud (Capital)'], 'Airai': ['Airai State'], 'Peleliu': ['Peleliu State']},
    ),
    'PY': CountryLocationConfig(
        region_label='Department',
        subregion_label='Municipality',
        regions=['Alto Paraguay', 'Alto Paraná', 'Amambay', 'Asunción', 'Boquerón', 'Caaguazú', 'Caazapá', 'Canindeyú', 'Central', 'Concepción', 'Cordillera', 'Guairá', 'Itapúa', 'Misiones', 'Ñeembucú', 'Paraguarí', 'Presidente Hayes', 'San Pedro'],
        subregions={'Asunción': ['Asunción City'], 'Central': ['Luque', 'San Lorenzo', 'Fernando de la Mora', 'Lambaré', 'Villa Elisa'], 'Alto Paraná': ['Ciudad del Este', 'Hernandarias', 'Minga Guazú'], 'Itapúa': ['Encarnación', 'Hohenau', 'Trinidad'], 'Concepción': ['Concepción City', 'Horqueta']},
    ),
    'QA': CountryLocationConfig(
        region_label='Municipality',
        subregion_label='Zone',
        regions=['Ad Dawhah', 'Al Khor', 'Al Rayyan', 'Al Shahaniyah', 'Al Shamal', 'Al Wakrah', 'Ash Shamal', 'Doha', 'Madinat ash Shamal', 'Umm Salal', 'Al Khawr wa adh Dhakhīrah', 'Ar Rayyān', 'Ash Shīḩānīyah', 'Az̧ Z̧a‘āyin'],
        subregions={'Doha': ['Doha City', 'West Bay', 'Al Sadd', 'Msheireb', 'The Pearl'], 'Al Rayyan': ['Al Rayyan City', 'Al Aziziyah', 'Muaither'], 'Al Wakrah': ['Al Wakrah City', 'Al Wukair'], 'Al Khor': ['Al Khor City', 'Al Dhakhira'], 'Umm Salal': ['Umm Salal Muhammad']},
    ),
    'RE': CountryLocationConfig(
        region_label='Territory',
        subregion_label='Locality',
        regions=['Réunion'],
        subregions={},
    ),
    'RO': CountryLocationConfig(
        region_label='County',
        subregion_label='City',
        regions=['Alba', 'Arad', 'Argeș', 'Bacău', 'Bihor', 'Bistrița-Năsăud', 'Botoșani', 'Brăila', 'Brașov', 'Bucharest', 'Buzău', 'Călărași', 'Caraș-Severin', 'Cluj', 'Constanța', 'Covasna', 'Dâmbovița', 'Dolj', 'Galați', 'Giurgiu', 'Gorj', 'Harghita', 'Hunedoara', 'Ialomița', 'Iași', 'Ilfov', 'Maramureș', 'Mehedinți', 'Mureș', 'Neamț', 'Olt', 'Prahova', 'Sălaj', 'Satu Mare', 'Sibiu', 'Suceava', 'Teleorman', 'Timiș', 'Tulcea', 'Vâlcea', 'Vaslui', 'Vrancea', 'București'],
        subregions={'Bucharest': ['Bucharest City'], 'Cluj': ['Cluj-Napoca', 'Dej', 'Turda', 'Câmpia Turzii'], 'Timiș': ['Timișoara', 'Lugoj', 'Jimbolia'], 'Iași': ['Iași City', 'Pașcani', 'Hârlău'], 'Constanța': ['Constanța City', 'Mangalia', 'Cernavodă'], 'Prahova': ['Ploiești', 'Câmpina', 'Sinaia', 'Bușteni'], 'Brașov': ['Brașov City', 'Codlea', 'Săcele', 'Predeal']},
    ),
    'RS': CountryLocationConfig(
        region_label='District',
        subregion_label='Municipality',
        regions=['Belgrade', 'Bor', 'Braničevo', 'Jablanica', 'Kolubara', 'Mačva', 'Moravica', 'Nišava', 'Pčinja', 'Pirot', 'Podunavlje', 'Pomoravlje', 'Rasina', 'Raška', 'Šumadija', 'Toplica', 'Vojvodina - South Bačka', 'Vojvodina - North Bačka', 'Vojvodina - West Bačka', 'Vojvodina - South Banat', 'Vojvodina - North Banat', 'Vojvodina - Central Banat', 'Vojvodina - Srem', 'Zaječar', 'Zlatibor', 'Beograd', 'Mačvanski okrug', 'Kolubarski okrug', 'Podunavski okrug', 'Braničevski okrug', 'Šumadijski okrug', 'Pomoravski okrug', 'Borski okrug', 'Zaječarski okrug', 'Zlatiborski okrug', 'Moravički okrug', 'Raški okrug', 'Rasinski okrug', 'Nišavski okrug', 'Toplički okrug', 'Pirotski okrug', 'Jablanički okrug', 'Pčinjski okrug', 'Kosovo-Metohija', 'Vojvodina'],
        subregions={'Belgrade': ['Belgrade City', 'Zemun', 'Novi Beograd', 'Rakovica', 'Palilula'], 'Vojvodina - South Bačka': ['Novi Sad', 'Subotica', 'Sombor', 'Zrenjanin'], 'Nišava': ['Niš', 'Pirot City', 'Prokuplje'], 'Šumadija': ['Kragujevac', 'Topola', 'Rača'], 'Rasina': ['Kruševac', 'Aleksandrovac'], 'Zlatibor': ['Užice', 'Čačak', 'Požega']},
    ),
    'RU': CountryLocationConfig(
        region_label='Federal Subject',
        subregion_label='City',
        regions=['Altai Krai', 'Altai Republic', 'Amur Oblast', 'Arkhangelsk Oblast', 'Astrakhan Oblast', 'Bashkortostan', 'Belgorod Oblast', 'Bryansk Oblast', 'Buryatia', 'Chechen Republic', 'Chelyabinsk Oblast', 'Chukotka', 'Chuvashia', 'Dagestan', 'Ingushetia', 'Irkutsk Oblast', 'Ivanovo Oblast', 'Jewish Autonomous Oblast', 'Kabardino-Balkaria', 'Kaliningrad Oblast', 'Kalmykia', 'Kaluga Oblast', 'Kamchatka Krai', 'Karachay-Cherkessia', 'Karelia', 'Kemerovo Oblast', 'Khabarovsk Krai', 'Khakassia', 'Khanty-Mansi', 'Kirov Oblast', 'Komi Republic', 'Kostroma Oblast', 'Krasnodar Krai', 'Krasnoyarsk Krai', 'Kurgan Oblast', 'Kursk Oblast', 'Leningrad Oblast', 'Lipetsk Oblast', 'Magadan Oblast', 'Mari El', 'Mordovia', 'Moscow', 'Moscow Oblast', 'Murmansk Oblast', 'Nenets Autonomous Okrug', 'Nizhny Novgorod Oblast', 'North Ossetia', 'Novgorod Oblast', 'Novosibirsk Oblast', 'Omsk Oblast', 'Orel Oblast', 'Orenburg Oblast', 'Penza Oblast', 'Perm Krai', 'Primorsky Krai', 'Pskov Oblast', 'Rostov Oblast', 'Ryazan Oblast', 'Saint Petersburg', 'Sakha Republic', 'Sakhalin Oblast', 'Samara Oblast', 'Saratov Oblast', 'Smolensk Oblast', 'Stavropol Krai', 'Sverdlovsk Oblast', 'Tambov Oblast', 'Tatarstan', 'Tomsk Oblast', 'Tula Oblast', 'Tuva', 'Tver Oblast', 'Tyumen Oblast', 'Udmurtia', 'Ulyanovsk Oblast', 'Vladimir Oblast', 'Volgograd Oblast', 'Vologda Oblast', 'Voronezh Oblast', 'Yamalo-Nenets', 'Yaroslavl Oblast', 'Zabaykalsky Krai', 'Adygeja, Respublika', 'Altaj, Respublika', 'Altajskij kraj', "Amurskaja oblast'", "Arhangel'skaja oblast'", "Astrahanskaja oblast'", 'Bashkortostan, Respublika', "Belgorodskaja oblast'", "Brjanskaja oblast'", 'Burjatija, Respublika', 'Chechenskaya Respublika', "Chelyabinskaya oblast'", 'Chukotskiy avtonomnyy okrug', 'Chuvashskaya Respublika', 'Dagestan, Respublika', 'Ingushetiya, Respublika', "Irkutskaja oblast'", "Ivanovskaja oblast'", 'Kamchatskiy kray', 'Kabardino-Balkarskaja Respublika', 'Karachayevo-Cherkesskaya Respublika', 'Krasnodarskij kraj', "Kemerovskaja oblast'", "Kaliningradskaja oblast'", "Kurganskaja oblast'", 'Habarovskij kraj', 'Hanty-Mansijskij avtonomnyj okrug', "Kirovskaja oblast'", 'Hakasija, Respublika', 'Kalmykija, Respublika', "Kaluzhskaya oblast'", 'Komi, Respublika', "Kostromskaja oblast'", 'Karelija, Respublika', "Kurskaja oblast'", 'Krasnojarskij kraj', "Leningradskaja oblast'", "Lipeckaja oblast'", "Magadanskaja oblast'", 'Marij Èl, Respublika', 'Mordovija, Respublika', "Moskovskaja oblast'", 'Moskva', "Murmanskaja oblast'", 'Neneckij avtonomnyj okrug', "Novgorodskaja oblast'", "Nizhegorodskaya oblast'", "Novosibirskaja oblast'", "Omskaja oblast'", "Orenburgskaja oblast'", "Orlovskaja oblast'", 'Permskij kraj', "Penzenskaja oblast'", 'Primorskij kraj', "Pskovskaja oblast'", "Rostovskaja oblast'", "Rjazanskaja oblast'", 'Saha, Respublika', "Sahalinskaja oblast'", "Samarskaja oblast'", "Saratovskaja oblast'", 'Severnaja Osetija, Respublika', "Smolenskaja oblast'", 'Sankt-Peterburg', "Stavropol'skij kraj", "Sverdlovskaja oblast'", 'Tatarstan, Respublika', "Tambovskaja oblast'", "Tomskaja oblast'", "Tul'skaja oblast'", "Tverskaja oblast'", 'Tyva, Respublika', "Tjumenskaja oblast'", 'Udmurtskaja Respublika', "Ul'janovskaja oblast'", "Volgogradskaja oblast'", "Vladimirskaja oblast'", "Vologodskaja oblast'", "Voronezhskaya oblast'", 'Jamalo-Neneckij avtonomnyj okrug', "Jaroslavskaja oblast'", "Evrejskaja avtonomnaja oblast'", "Zabajkal'skij kraj"],
        subregions={'Moscow': ['Moscow City', 'Zelenograd', 'Troitsk', 'Shcherbinka'], 'Saint Petersburg': ['Saint Petersburg City', 'Peterhof', 'Pushkin'], 'Tatarstan': ['Kazan', 'Naberezhnye Chelny', 'Nizhnekamsk', 'Almetyevsk'], 'Sverdlovsk Oblast': ['Yekaterinburg', 'Nizhny Tagil', 'Kamensk-Uralsky'], 'Novosibirsk Oblast': ['Novosibirsk', 'Berdsk', 'Ob'], 'Krasnodar Krai': ['Krasnodar', 'Sochi', 'Novorossiysk', 'Armavir'], 'Krasnoyarsk Krai': ['Krasnoyarsk', 'Norilsk', 'Achinsk'], 'Rostov Oblast': ['Rostov-on-Don', 'Taganrog', 'Shakhty', 'Volgodonsk']},
    ),
    'RW': CountryLocationConfig(
        region_label='Province',
        subregion_label='District',
        regions=['Kigali', 'Northern', 'Southern', 'City of Kigali', 'Eastern', 'Western'],
        subregions={},
    ),
    'SA': CountryLocationConfig(
        region_label='Region',
        subregion_label='Governorate',
        regions=['Al Bahah', 'Al Jawf', 'Al Madinah', 'Al Qassim', 'Asir', 'Eastern Province', "Ha'il", 'Jizan', 'Mecca', 'Najran', 'Northern Borders', 'Riyadh', 'Tabuk', 'Ar Riyāḑ', 'Makkah al Mukarramah', 'Al Madīnah al Munawwarah', 'Ash Sharqīyah', 'Al Qaşīm', 'Al Ḩudūd ash Shamālīyah', 'Jāzān'],
        subregions={'Riyadh': ['Riyadh City', 'Ad Diriyah', 'Al Kharj', 'Marat', 'Dawadmi'], 'Mecca': ['Jeddah', 'Mecca City', 'Taif', 'Yanbu'], 'Eastern Province': ['Dammam', 'Al-Ahsa', 'Dhahran', 'Al Khobar', 'Jubail'], 'Al Madinah': ['Medina City', 'Yanbu City', 'Mahd adh Dhahab'], 'Asir': ['Abha', 'Khamis Mushait', 'Jizan City', 'Najran City'], 'Jizan': ['Jizan City', 'Sabya', 'Samtah']},
    ),
    'SB': CountryLocationConfig(
        region_label='Province',
        subregion_label='Constituency',
        regions=['Capital Territory (Honiara)', 'Central Province', 'Choiseul Province', 'Guadalcanal Province', 'Isabel Province', 'Makira-Ulawa Province', 'Malaita Province', 'Rennell and Bellona Province', 'Temotu Province', 'Western Province', 'Central', 'Choiseul', 'Guadalcanal', 'Isabel', 'Makira-Ulawa', 'Malaita', 'Rennell and Bellona', 'Temotu', 'Western'],
        subregions={'Capital Territory (Honiara)': ['Honiara City'], 'Guadalcanal Province': ['Gold Ridge', 'North Guadalcanal', 'South Guadalcanal'], 'Malaita Province': ['Auki', 'North Malaita', 'South Malaita'], 'Western Province': ['Gizo', 'Munda', 'Noro'], 'Central Province': ['Tulagi', 'Russell Islands']},
    ),
    'SC': CountryLocationConfig(
        region_label='District',
        subregion_label='Sub-District',
        regions=['Victoria', 'Anse Boileau', 'Beau Vallon', 'Anse aux Pins', 'Anse Etoile', 'Au Cap', 'Anse Royale', 'Baie Lazare', 'Baie Sainte Anne', 'Bel Air', 'Bel Ombre', 'Cascade', 'Glacis', 'Grand Anse Mahe', 'Grand Anse Praslin', 'La Digue', 'English River', 'Mont Buxton', 'Mont Fleuri', 'Plaisance', 'Pointe Larue', 'Port Glaud', 'Saint Louis', 'Takamaka', 'Les Mamelles', 'Roche Caiman', 'Ile Perseverance I', 'Ile Perseverance II'],
        subregions={},
    ),
    'SD': CountryLocationConfig(
        region_label='State',
        subregion_label='Locality',
        regions=['Khartoum', 'Kassala', 'Darfur', 'Central Darfur', 'East Darfur', 'North Darfur', 'South Darfur', 'West Darfur', 'Gedaref', 'West Kordofan', 'Gezira', 'North Kordofan', 'South Kordofan', 'Blue Nile', 'Northern', 'River Nile', 'White Nile', 'Red Sea', 'Sennar'],
        subregions={},
    ),
    'SE': CountryLocationConfig(
        region_label='County',
        subregion_label='Municipality',
        regions=['Blekinge County', 'Dalarna County', 'Gävleborg County', 'Gotland County', 'Halland County', 'Jämtland County', 'Jönköping County', 'Kalmar County', 'Kronoberg County', 'Norrbotten County', 'Örebro County', 'Östergötland County', 'Skåne County', 'Södermanland County', 'Stockholm County', 'Uppsala County', 'Värmland County', 'Västerbotten County', 'Västernorrland County', 'Västmanland County', 'Västra Götaland County', 'Stockholms län [SE-01]', 'Västerbottens län [SE-24]', 'Norrbottens län [SE-25]', 'Uppsala län [SE-03]', 'Södermanlands län [SE-04]', 'Östergötlands län [SE-05]', 'Jönköpings län [SE-06]', 'Kronobergs län [SE-07]', 'Kalmar län [SE-08]', 'Gotlands län [SE-09]', 'Blekinge län [SE-10]', 'Skåne län [SE-12]', 'Hallands län [SE-13]', 'Västra Götalands län [SE-14]', 'Värmlands län [SE-17]', 'Örebro län [SE-18]', 'Västmanlands län [SE-19]', 'Dalarnas län [SE-20]', 'Gävleborgs län [SE-21]', 'Västernorrlands län [SE-22]', 'Jämtlands län [SE-23]'],
        subregions={'Stockholm County': ['Stockholm City', 'Huddinge', 'Järfälla', 'Solna', 'Haninge'], 'Västra Götaland County': ['Gothenburg', 'Mölndal', 'Borås', 'Trollhättan'], 'Skåne County': ['Malmö', 'Helsingborg', 'Kristianstad', 'Lund'], 'Östergötland County': ['Linköping', 'Norrköping', 'Motala'], 'Uppsala County': ['Uppsala City', 'Enköping'], 'Jönköping County': ['Jönköping City', 'Huskvarna', 'Nässjö'], 'Norrbotten County': ['Luleå', 'Piteå', 'Boden', 'Kiruna']},
    ),
    'SG': CountryLocationConfig(
        region_label='Region',
        subregion_label='Planning Area',
        regions=['Central Region', 'East Region', 'North Region', 'North-East Region', 'West Region', 'Central Singapore', 'North East', 'North West', 'South East', 'South West'],
        subregions={'Central Region': ['Downtown Core', 'Marina Bay', 'Orchard', 'Newton', 'Tanglin', 'Bishan'], 'North Region': ['Woodlands', 'Sembawang', 'Yishun', 'Mandai'], 'North-East Region': ['Punggol', 'Sengkang', 'Hougang', 'Serangoon'], 'East Region': ['Tampines', 'Pasir Ris', 'Bedok', 'Changi'], 'West Region': ['Jurong East', 'Jurong West', 'Bukit Batok', 'Clementi', 'Choa Chu Kang']},
    ),
    'SH': CountryLocationConfig(
        region_label='Region',
        subregion_label='District',
        regions=['Ascension', 'Saint Helena', 'Tristan da Cunha'],
        subregions={},
    ),
    'SI': CountryLocationConfig(
        region_label='Statistical Region',
        subregion_label='Municipality',
        regions=['Central Slovenia', 'Coastal-Karst', 'Gorenjska', 'Goriška', 'Koroška', 'Littoral-Inner Carniola', 'Lower Sava', 'Obalno-kraška', 'Pomurje', 'Posavje', 'Savinja', 'Southeast Slovenia', 'Štajerska', 'Upper Carniola', 'Zasavje', 'Ajdovščina', 'Beltinci', 'Bled', 'Bohinj', 'Borovnica', 'Bovec', 'Brda', 'Brezovica', 'Brežice', 'Tišina', 'Celje', 'Cerklje na Gorenjskem', 'Cerknica', 'Cerkno', 'Črenšovci', 'Črna na Koroškem', 'Črnomelj', 'Destrnik', 'Divača', 'Dobrepolje', 'Dobrova-Polhov Gradec', 'Dol pri Ljubljani', 'Domžale', 'Dornava', 'Dravograd', 'Duplek', 'Gorenja vas-Poljane', 'Gorišnica', 'Gornja Radgona', 'Gornji Grad', 'Gornji Petrovci', 'Grosuplje', 'Šalovci', 'Hrastnik', 'Hrpelje-Kozina', 'Idrija', 'Ig', 'Ilirska Bistrica', 'Ivančna Gorica', 'Izola', 'Jesenice', 'Juršinci', 'Kamnik', 'Kanal ob Soči', 'Kidričevo', 'Kobarid', 'Kobilje', 'Kočevje', 'Komen', 'Koper', 'Kozje', 'Kranj', 'Kranjska Gora', 'Krško', 'Kungota', 'Kuzma', 'Laško', 'Lenart', 'Lendava', 'Litija', 'Ljubljana', 'Ljubno', 'Ljutomer', 'Logatec', 'Loška dolina', 'Loški Potok', 'Luče', 'Lukovica', 'Majšperk', 'Maribor', 'Medvode', 'Mengeš', 'Metlika', 'Mežica', 'Miren-Kostanjevica', 'Mislinja', 'Moravče', 'Moravske Toplice', 'Mozirje', 'Murska Sobota', 'Muta', 'Naklo', 'Nazarje', 'Nova Gorica', 'Novo Mesto', 'Odranci', 'Ormož', 'Osilnica', 'Pesnica', 'Piran', 'Pivka', 'Podčetrtek', 'Podvelka', 'Postojna', 'Preddvor', 'Ptuj', 'Puconci', 'Rače-Fram', 'Radeče', 'Radenci', 'Radlje ob Dravi', 'Radovljica', 'Ravne na Koroškem', 'Ribnica', 'Rogašovci', 'Rogaška Slatina', 'Rogatec', 'Ruše', 'Semič', 'Sevnica', 'Sežana', 'Slovenj Gradec', 'Slovenska Bistrica', 'Slovenske Konjice', 'Starše', 'Sveti Jurij ob Ščavnici', 'Šenčur', 'Šentilj', 'Šentjernej', 'Šentjur', 'Škocjan', 'Škofja Loka', 'Škofljica', 'Šmarje pri Jelšah', 'Šmartno ob Paki', 'Šoštanj', 'Štore', 'Tolmin', 'Trbovlje', 'Trebnje', 'Tržič', 'Turnišče', 'Velenje', 'Velike Lašče', 'Videm', 'Vipava', 'Vitanje', 'Vodice', 'Vojnik', 'Vrhnika', 'Vuzenica', 'Zagorje ob Savi', 'Zavrč', 'Zreče', 'Železniki', 'Žiri', 'Benedikt', 'Bistrica ob Sotli', 'Bloke', 'Braslovče', 'Cankova', 'Cerkvenjak', 'Dobje', 'Dobrna', 'Dobrovnik', 'Dolenjske Toplice', 'Grad', 'Hajdina', 'Hoče-Slivnica', 'Hodoš', 'Horjul', 'Jezersko', 'Komenda', 'Kostel', 'Križevci', 'Lovrenc na Pohorju', 'Markovci', 'Miklavž na Dravskem polju', 'Mirna Peč', 'Oplotnica', 'Podlehnik', 'Polzela', 'Prebold', 'Prevalje', 'Razkrižje', 'Ribnica na Pohorju', 'Selnica ob Dravi', 'Sodražica', 'Solčava', 'Sveta Ana', 'Sveti Andraž v Slovenskih goricah', 'Šempeter-Vrtojba', 'Tabor', 'Trnovska Vas', 'Trzin', 'Velika Polana', 'Veržej', 'Vransko', 'Žalec', 'Žetale', 'Žirovnica', 'Žužemberk', 'Šmartno pri Litiji', 'Apače', 'Cirkulane', 'Kostanjevica na Krki', 'Makole', 'Mokronog-Trebelno', 'Poljčane', 'Renče-Vogrsko', 'Središče ob Dravi', 'Straža', 'Sveta Trojica v Slovenskih goricah', 'Sveti Tomaž', 'Šmarješke Toplice', 'Gorje', 'Log-Dragomer', 'Rečica ob Savinji', 'Sveti Jurij v Slovenskih goricah', 'Šentrupert', 'Mirna', 'Ankaran'],
        subregions={'Central Slovenia': ['Ljubljana', 'Domžale', 'Kamnik', 'Grosuplje'], 'Gorenjska': ['Kranj', 'Škofja Loka', 'Jesenice', 'Tržič'], 'Savinja': ['Celje', 'Velenje', 'Žalec'], 'Koroška': ['Slovenj Gradec', 'Ravne na Koroškem', 'Dravograd'], 'Coastal-Karst': ['Koper', 'Piran', 'Portorož', 'Izola'], 'Pomurje': ['Murska Sobota', 'Ljutomer']},
    ),
    'SJ': CountryLocationConfig(
        region_label='Territory',
        subregion_label='Locality',
        regions=['Svalbard and Jan Mayen'],
        subregions={},
    ),
    'SK': CountryLocationConfig(
        region_label='Region',
        subregion_label='District',
        regions=['Banská Bystrica Region', 'Bratislava Region', 'Košice Region', 'Nitra Region', 'Prešov Region', 'Trenčín Region', 'Trnava Region', 'Žilina Region', 'Banskobystrický kraj', 'Bratislavský kraj', 'Košický kraj', 'Nitriansky kraj', 'Prešovský kraj', 'Trnavský kraj', 'Trenčiansky kraj', 'Žilinský kraj'],
        subregions={'Bratislava Region': ['Bratislava City', 'Malacky', 'Pezinok', 'Senec'], 'Košice Region': ['Košice City', 'Spišská Nová Ves', 'Rožňava'], 'Banská Bystrica Region': ['Banská Bystrica City', 'Zvolen', 'Rimavská Sobota'], 'Prešov Region': ['Prešov City', 'Poprad', 'Stará Ľubovňa'], 'Nitra Region': ['Nitra City', 'Komárno', 'Šaľa'], 'Žilina Region': ['Žilina City', 'Martin', 'Čadca']},
    ),
    'SL': CountryLocationConfig(
        region_label='Province',
        subregion_label='District',
        regions=['Western Area', 'Northern', 'Southern', 'Eastern', 'North Western', 'Western Area (Freetown)'],
        subregions={},
    ),
    'SM': CountryLocationConfig(
        region_label='Castle',
        subregion_label='Locality',
        regions=['Acquaviva', 'Borgo Maggiore', 'Chiesanuova', 'Domagnano', 'Faetano', 'Fiorentino', 'Montegiardino', 'San Marino City', 'Serravalle', 'Città di San Marino'],
        subregions={'San Marino City': ['San Marino City'], 'Serravalle': ['Serravalle', 'Dogana'], 'Borgo Maggiore': ['Borgo Maggiore'], 'Domagnano': ['Domagnano'], 'Fiorentino': ['Fiorentino']},
    ),
    'SN': CountryLocationConfig(
        region_label='Region',
        subregion_label='Department',
        regions=['Dakar', 'Thiès', 'Saint-Louis', 'Diourbel', 'Fatick', 'Kaffrine', 'Kolda', 'Kédougou', 'Kaolack', 'Louga', 'Matam', 'Sédhiou', 'Tambacounda', 'Ziguinchor'],
        subregions={},
    ),
    'SO': CountryLocationConfig(
        region_label='Region',
        subregion_label='District',
        regions=['Banaadir', 'Puntland', 'Somaliland', 'Awdal', 'Bakool', 'Bari', 'Bay', 'Galguduud', 'Gedo', 'Hiiraan', 'Jubbada Dhexe', 'Jubbada Hoose', 'Mudug', 'Nugaal', 'Sanaag', 'Shabeellaha Dhexe', 'Shabeellaha Hoose', 'Sool', 'Togdheer', 'Woqooyi Galbeed'],
        subregions={},
    ),
    'SR': CountryLocationConfig(
        region_label='District',
        subregion_label='Resort',
        regions=['Brokopondo', 'Commewijne', 'Coronie', 'Marowijne', 'Nickerie', 'Para', 'Paramaribo', 'Saramacca', 'Sipaliwini', 'Wanica'],
        subregions={'Paramaribo': ['Paramaribo City', 'Livorno', 'Beekhuizen'], 'Wanica': ['Lelydorp', 'Uitvlugt'], 'Nickerie': ['Nieuw Nickerie', 'Wageningen'], 'Commewijne': ['Nieuw Amsterdam', 'Meerzorg'], 'Saramacca': ['Groningen', 'Uitkijk']},
    ),
    'SS': CountryLocationConfig(
        region_label='State',
        subregion_label='County',
        regions=['Central Equatoria', 'Jonglei', 'Upper Nile', 'Northern Bahr el Ghazal', 'Western Bahr el Ghazal', 'Eastern Equatoria', 'Western Equatoria', 'Lakes', 'Unity', 'Warrap'],
        subregions={},
    ),
    'ST': CountryLocationConfig(
        region_label='District',
        subregion_label='Parish',
        regions=['Água Grande', 'Mé-Zóchi', 'Cantagalo', 'Caué', 'Lembá', 'Lobata', 'Príncipe'],
        subregions={},
    ),
    'SV': CountryLocationConfig(
        region_label='Department',
        subregion_label='Municipality',
        regions=['Ahuachapán', 'Cabañas', 'Chalatenango', 'Cuscatlán', 'La Libertad', 'La Paz', 'La Unión', 'Morazán', 'San Miguel', 'San Salvador', 'San Vicente', 'Santa Ana', 'Sonsonate', 'Usulután'],
        subregions={'San Salvador': ['San Salvador City', 'Mejicanos', 'Soyapango', 'Apopa', 'Ayutuxtepeque'], 'Santa Ana': ['Santa Ana City', 'Chalchuapa', 'Metapán'], 'La Libertad': ['Santa Tecla', 'Antiguo Cuscatlán', 'Quezaltepeque'], 'Sonsonate': ['Sonsonate City', 'Acajutla', 'Nahuizalco'], 'San Miguel': ['San Miguel City', 'Moncagua', 'Ciudad Barrios']},
    ),
    'SX': CountryLocationConfig(
        region_label='Territory',
        subregion_label='Locality',
        regions=['Sint Maarten (Dutch part)'],
        subregions={},
    ),
    'SY': CountryLocationConfig(
        region_label='Governorate',
        subregion_label='District',
        regions=['Al-Hasakah', 'Al-Raqqah', 'Aleppo', 'As-Suwayda', 'Damascus', 'Daraa', 'Deir ez-Zor', 'Hama', 'Homs', 'Idlib', 'Latakia', 'Quneitra', 'Rif Dimashq', 'Tartus', 'Dimashq', "Dar'ā", 'Dayr az Zawr', 'Ḩimş', 'Ḩalab', 'Ḩamāh', 'Al Lādhiqīyah', 'Al Qunayţirah', 'Ar Raqqah'],
        subregions={'Damascus': ['Damascus City'], 'Aleppo': ['Aleppo City', 'Al-Bab', 'Azaz', 'Afrin'], 'Homs': ['Homs City', 'Palmyra', 'Al-Qusayr'], 'Hama': ['Hama City', 'Masyaf', 'Salamiyah'], 'Latakia': ['Latakia City', 'Jableh', 'Al-Haffah'], 'Idlib': ['Idlib City', 'Maaret al-Numan', 'Jisr al-Shughur'], 'Rif Dimashq': ['Douma', 'Al-Qaboun', 'Darayya'], 'Daraa': ['Daraa City', 'Bosra']},
    ),
    'SZ': CountryLocationConfig(
        region_label='Region',
        subregion_label='Inkhundla',
        regions=['Hhohho', 'Manzini', 'Lubombo', 'Shiselweni'],
        subregions={},
    ),
    'TC': CountryLocationConfig(
        region_label='Territory',
        subregion_label='Locality',
        regions=['Turks and Caicos Islands'],
        subregions={},
    ),
    'TD': CountryLocationConfig(
        region_label='Region',
        subregion_label='Department',
        regions=["N'Djamena", 'Logone Occidental', 'Moyen-Chari', 'Batha', 'Bahr el Ghazal', 'Borkou', 'Chari-Baguirmi', 'Ennedi-Est', 'Ennedi-Ouest', 'Guéra', 'Hadjer Lamis', 'Kanem', 'Lac', 'Logone-Oriental', 'Mandoul', 'Mayo-Kebbi-Est', 'Mayo-Kebbi-Ouest', 'Ville de Ndjamena', 'Ouaddaï', 'Salamat', 'Sila', 'Tandjilé', 'Tibesti', 'Wadi Fira'],
        subregions={},
    ),
    'TF': CountryLocationConfig(
        region_label='Territory',
        subregion_label='Locality',
        regions=['French Southern Territories'],
        subregions={},
    ),
    'TG': CountryLocationConfig(
        region_label='Region',
        subregion_label='Prefecture',
        regions=['Maritime', 'Plateaux', 'Centrale', 'Kara', 'Maritime (Région)', 'Savanes'],
        subregions={},
    ),
    'TH': CountryLocationConfig(
        region_label='Province',
        subregion_label='District',
        regions=['Amnat Charoen', 'Ang Thong', 'Bangkok', 'Bueng Kan', 'Buri Ram', 'Chachoengsao', 'Chai Nat', 'Chaiyaphum', 'Chanthaburi', 'Chiang Mai', 'Chiang Rai', 'Chon Buri', 'Chumphon', 'Kalasin', 'Kamphaeng Phet', 'Kanchanaburi', 'Khon Kaen', 'Krabi', 'Lampang', 'Lamphun', 'Loei', 'Lop Buri', 'Mae Hong Son', 'Maha Sarakham', 'Mukdahan', 'Nakhon Nayok', 'Nakhon Pathom', 'Nakhon Phanom', 'Nakhon Ratchasima', 'Nakhon Sawan', 'Nakhon Si Thammarat', 'Nan', 'Narathiwat', 'Nong Bua Lam Phu', 'Nong Khai', 'Nonthaburi', 'Pathum Thani', 'Pattani', 'Phang Nga', 'Phatthalung', 'Phayao', 'Phetchabun', 'Phetchaburi', 'Phichit', 'Phitsanulok', 'Phra Nakhon Si Ayutthaya', 'Phrae', 'Phuket', 'Prachin Buri', 'Prachuap Khiri Khan', 'Ranong', 'Ratchaburi', 'Rayong', 'Roi Et', 'Sa Kaeo', 'Sakon Nakhon', 'Samut Prakan', 'Samut Sakhon', 'Samut Songkhram', 'Saraburi', 'Satun', 'Sing Buri', 'Si Sa Ket', 'Songkhla', 'Sukhothai', 'Suphanburi', 'Surat Thani', 'Surin', 'Tak', 'Trang', 'Trat', 'Ubon Ratchathani', 'Udon Thani', 'Uthai Thani', 'Uttaradit', 'Yala', 'Yasothon', 'Krung Thep Maha Nakhon', 'Suphan Buri', 'Phangnga', 'Phatthaya'],
        subregions={'Bangkok': ['Phra Nakhon', 'Dusit', 'Pathum Wan', 'Bang Rak', 'Watthana'], 'Chiang Mai': ['Mueang Chiang Mai', 'Hang Dong', 'San Sai', 'Mae Rim'], 'Chon Buri': ['Mueang Chon Buri', 'Pattaya', 'Si Racha', 'Bang Lamung'], 'Nakhon Ratchasima': ['Mueang Nakhon Ratchasima', 'Pak Chong', 'Bua Yai'], 'Phuket': ['Mueang Phuket', 'Kathu', 'Thalang'], 'Khon Kaen': ['Mueang Khon Kaen', 'Nam Phong', 'Chum Phae'], 'Songkhla': ['Hat Yai', 'Mueang Songkhla', 'Na Thawi']},
    ),
    'TJ': CountryLocationConfig(
        region_label='Region',
        subregion_label='District',
        regions=['Dushanbe City', 'Gorno-Badakhshan', 'Khatlon', 'Regions of Republican Subordination', 'Sughd', 'Dushanbe', 'Kŭhistoni Badakhshon', 'nohiyahoi tobei jumhurí'],
        subregions={'Dushanbe City': ['Dushanbe City'], 'Sughd': ['Khujand', 'Istaravshan', 'Panjakent', 'Isfara'], 'Khatlon': ['Bokhtar', 'Kulob', 'Qurghonteppa'], 'Gorno-Badakhshan': ['Khorugh', 'Ishkoshim', 'Rushan'], 'Regions of Republican Subordination': ['Vahdat', 'Tursunzoda', 'Hisor']},
    ),
    'TK': CountryLocationConfig(
        region_label='Territory',
        subregion_label='Locality',
        regions=['Tokelau'],
        subregions={},
    ),
    'TL': CountryLocationConfig(
        region_label='Municipality',
        subregion_label='Administrative Post',
        regions=['Aileu', 'Ainaro', 'Baucau', 'Bobonaro', 'Cova Lima', 'Dili', 'Ermera', 'Lautem', 'Liquiçá', 'Manatuto', 'Manufahi', 'Oecusse', 'Viqueque', 'Lautein', 'Likisá', 'Oekusi-Ambenu', 'Vikeke'],
        subregions={'Dili': ['Vera Cruz', 'Dom Aleixo', 'Nain Feto', 'Cristo Rei'], 'Baucau': ['Baucau Town', 'Laga', 'Venilale', 'Quelicai'], 'Ermera': ['Ermera Town', 'Atsabe', 'Hatulia'], 'Bobonaro': ['Maliana', 'Balibo', 'Atabae'], 'Oecusse': ['Oecusse Town', 'Passabe', 'Nitibe']},
    ),
    'TM': CountryLocationConfig(
        region_label='Province',
        subregion_label='District',
        regions=['Ahal', 'Ashgabat', 'Balkan', 'Daşoguz', 'Lebap', 'Mary', 'Aşgabat'],
        subregions={'Ashgabat': ['Ashgabat City'], 'Ahal': ['Abadan', 'Ak Bugday', 'Babadayhany', 'Büzmeyin'], 'Balkan': ['Turkmenbashi', 'Balkanabat', 'Gumdag', 'Serdar'], 'Daşoguz': ['Daşoguz City', 'Gurbansoltan Eje', 'Köneürgench'], 'Lebap': ['Türkmenabat', 'Farap', 'Halaç', 'Çärjew'], 'Mary': ['Mary City', 'Bayramaly', 'Yolöten', 'Tagtabazar']},
    ),
    'TN': CountryLocationConfig(
        region_label='Governorate',
        subregion_label='Delegation',
        regions=['Tunis', 'Sfax', 'Sousse', "L'Ariana", 'Ben Arous', 'La Manouba', 'Nabeul', 'Zaghouan', 'Bizerte', 'Béja', 'Jendouba', 'Le Kef', 'Siliana', 'Kairouan', 'Kasserine', 'Sidi Bouzid', 'Monastir', 'Mahdia', 'Gafsa', 'Tozeur', 'Kébili', 'Gabès', 'Médenine', 'Tataouine'],
        subregions={},
    ),
    'TO': CountryLocationConfig(
        region_label='Division',
        subregion_label='Island',
        regions=["Ha'apai", 'Tongatapu', "Vava'u", "'Eua", 'Ongo Niua', 'Niuas'],
        subregions={'Tongatapu': ["Nuku'alofa", "Mu'a", 'Lapaha', 'Neiafu'], "Vava'u": ['Neiafu', 'Pangaimotu'], "Ha'apai": ['Pangai', "Ha'afeva"], "'Eua": ["'Ohonua", 'Futu'], 'Ongo Niua': ["Niuafo'ou", 'Niuatoputapu']},
    ),
    'TR': CountryLocationConfig(
        region_label='Province',
        subregion_label='District',
        regions=['Adana', 'Adıyaman', 'Afyonkarahisar', 'Ağrı', 'Aksaray', 'Amasya', 'Ankara', 'Antalya', 'Ardahan', 'Artvin', 'Aydın', 'Balıkesir', 'Bartın', 'Batman', 'Bayburt', 'Bilecik', 'Bingöl', 'Bitlis', 'Bolu', 'Burdur', 'Bursa', 'Çanakkale', 'Çankırı', 'Çorum', 'Denizli', 'Diyarbakır', 'Düzce', 'Edirne', 'Elazığ', 'Erzincan', 'Erzurum', 'Eskişehir', 'Gaziantep', 'Giresun', 'Gümüşhane', 'Hakkari', 'Hatay', 'Iğdır', 'Isparta', 'Istanbul', 'İzmir', 'Kahramanmaraş', 'Karabük', 'Karaman', 'Kars', 'Kastamonu', 'Kayseri', 'Kırıkkale', 'Kırklareli', 'Kırşehir', 'Kilis', 'Kocaeli', 'Konya', 'Kütahya', 'Malatya', 'Manisa', 'Mardin', 'Mersin', 'Muğla', 'Muş', 'Nevşehir', 'Niğde', 'Ordu', 'Osmaniye', 'Rize', 'Sakarya', 'Samsun', 'Şanlıurfa', 'Siirt', 'Sinop', 'Sivas', 'Şırnak', 'Tekirdağ', 'Tokat', 'Trabzon', 'Tunceli', 'Uşak', 'Van', 'Yalova', 'Yozgat', 'Zonguldak'],
        subregions={'Istanbul': ['Fatih', 'Beyoğlu', 'Beşiktaş', 'Kadıköy', 'Üsküdar', 'Bakırköy'], 'Ankara': ['Çankaya', 'Keçiören', 'Mamak', 'Yenimahalle', 'Altındağ'], 'İzmir': ['Konak', 'Bornova', 'Karşıyaka', 'Buca', 'Çiğli'], 'Antalya': ['Muratpaşa', 'Konyaaltı', 'Kepez', 'Serik'], 'Bursa': ['Osmangazi', 'Yıldırım', 'Nilüfer', 'Gemlik'], 'Adana': ['Seyhan', 'Yüreğir', 'Çukurova', 'Sarıçam'], 'Gaziantep': ['Şahinbey', 'Şehitkamil', 'Nizip']},
    ),
    'TT': CountryLocationConfig(
        region_label='Region',
        subregion_label='Community',
        regions=['Arima', 'Chaguanas', 'Couva-Tabaquite-Talparo', 'Diego Martin', 'Gulf of Paria', 'Mayaro-Rio Claro', 'Penal-Debe', 'Point Fortin', 'Port of Spain', 'Princes Town', 'San Fernando', 'San Juan-Laventille', 'Sangre Grande', 'Siparia', 'Tobago', 'Tunapuna-Piarco'],
        subregions={'Port of Spain': ['Port of Spain City'], 'San Fernando': ['San Fernando City'], 'Chaguanas': ['Chaguanas Borough'], 'Tobago': ['Scarborough', 'Plymouth', 'Speyside'], 'Arima': ['Arima Borough'], 'Tunapuna-Piarco': ['Tunapuna', 'Piarco', 'St. Augustine']},
    ),
    'TV': CountryLocationConfig(
        region_label='Island',
        subregion_label='Village',
        regions=['Funafuti', 'Nanumanga', 'Nanumea', 'Niulakita', 'Niutao', 'Nui', 'Nukufetau', 'Nukulaelae', 'Vaitupu', 'Nanumaga'],
        subregions={'Funafuti': ['Fongafale', 'Senala', 'Alapi'], 'Vaitupu': ['Asau'], 'Nanumea': ['Lolua'], 'Nanumanga': ['Tonga'], 'Niutao': ['Kulia']},
    ),
    'TW': CountryLocationConfig(
        region_label='County/City',
        subregion_label='Township',
        regions=['Changhua County', 'Chiayi City', 'Chiayi County', 'Hsinchu City', 'Hsinchu County', 'Hualien County', 'Kaohsiung City', 'Keelung City', 'Kinmen County', 'Lienchiang County', 'Miaoli County', 'Nantou County', 'New Taipei City', 'Penghu County', 'Pingtung County', 'Taichung City', 'Tainan City', 'Taipei City', 'Taitung County', 'Taoyuan City', 'Yilan County', 'Yunlin County', 'Changhua', 'Chiayi', 'Hsinchu', 'Hualien', 'Yilan', 'Keelung', 'Kaohsiung', 'Kinmen', 'Lienchiang', 'Miaoli', 'Nantou', 'New Taipei', 'Penghu', 'Pingtung', 'Taoyuan', 'Tainan', 'Taipei', 'Taitung', 'Taichung', 'Yunlin'],
        subregions={'Taipei City': ['Zhongzheng', "Da'an", 'Zhongshan', 'Xinyi', 'Shilin'], 'New Taipei City': ['Banqiao', 'Sanchong', 'Yonghe', 'Zhonghe', 'Xindian'], 'Taichung City': ['Taichung Central', 'Beitun', 'Xitun', 'Nantun'], 'Kaohsiung City': ['Lingya', 'Xinxing', 'Zuoying', 'Sanmin', 'Gushan'], 'Tainan City': ['East District', 'West District', 'Anping', 'Annan'], 'Taoyuan City': ['Taoyuan District', 'Zhongli', 'Pingzhen']},
    ),
    'TZ': CountryLocationConfig(
        region_label='Region',
        subregion_label='District',
        regions=['Dar es Salaam', 'Arusha', 'Mwanza', 'Dodoma', 'Iringa', 'Kagera', 'Pemba North', 'Zanzibar North', 'Kigoma', 'Kilimanjaro', 'Pemba South', 'Zanzibar South', 'Lindi', 'Mara', 'Mbeya', 'Zanzibar West', 'Morogoro', 'Mtwara', 'Coast', 'Rukwa', 'Ruvuma', 'Shinyanga', 'Singida', 'Tabora', 'Tanga', 'Manyara', 'Geita', 'Katavi', 'Njombe', 'Simiyu', 'Songwe'],
        subregions={},
    ),
    'UA': CountryLocationConfig(
        region_label='Oblast',
        subregion_label='District',
        regions=['Cherkasy Oblast', 'Chernihiv Oblast', 'Chernivtsi Oblast', 'Crimea Republic', 'Dnipropetrovsk Oblast', 'Donetsk Oblast', 'Ivano-Frankivsk Oblast', 'Kharkiv Oblast', 'Kherson Oblast', 'Khmelnytskyi Oblast', 'Kirovohrad Oblast', 'Kyiv City', 'Kyiv Oblast', 'Luhansk Oblast', 'Lviv Oblast', 'Mykolaiv Oblast', 'Odessa Oblast', 'Poltava Oblast', 'Rivne Oblast', 'Sumy Oblast', 'Ternopil Oblast', 'Vinnytsia Oblast', 'Volyn Oblast', 'Zakarpattia Oblast', 'Zaporizhzhia Oblast', 'Zhytomyr Oblast', 'Vinnytska oblast', 'Volynska oblast', 'Luhanska oblast', 'Dnipropetrovska oblast', 'Donetska oblast', 'Zhytomyrska oblast', 'Zakarpatska oblast', 'Zaporizka oblast', 'Ivano-Frankivska oblast', 'Kyiv', 'Kyivska oblast', 'Kirovohradska oblast', 'Sevastopol', 'Avtonomna Respublika Krym', 'Lvivska oblast', 'Mykolaivska oblast', 'Odeska oblast', 'Poltavska oblast', 'Rivnenska oblast', 'Sumska oblast', 'Ternopilska oblast', 'Kharkivska oblast', 'Khersonska oblast', 'Khmelnytska oblast', 'Cherkaska oblast', 'Chernihivska oblast', 'Chernivetska oblast'],
        subregions={'Kyiv City': ['Kyiv City'], 'Kyiv Oblast': ['Brovary', 'Boryspil', 'Vasylkiv', 'Bucha', 'Irpin'], 'Lviv Oblast': ['Lviv City', 'Stryi', 'Drohobych', 'Boryslav'], 'Kharkiv Oblast': ['Kharkiv City', 'Poltava City', 'Sumy City'], 'Odessa Oblast': ['Odessa City', 'Mykolaiv City', 'Kherson City'], 'Dnipropetrovsk Oblast': ['Dnipro City', 'Kryvyi Rih', 'Kamianske'], 'Donetsk Oblast': ['Donetsk City', 'Mariupol', 'Kramatorsk', 'Sloviansk']},
    ),
    'UG': CountryLocationConfig(
        region_label='Region',
        subregion_label='District',
        regions=['Central', 'Eastern', 'Northern', 'Western'],
        subregions={},
    ),
    'UM': CountryLocationConfig(
        region_label='Region',
        subregion_label='District',
        regions=['Johnston Atoll', 'Midway Islands', 'Navassa Island', 'Wake Island', 'Baker Island', 'Howland Island', 'Jarvis Island', 'Kingman Reef', 'Palmyra Atoll'],
        subregions={},
    ),
    'US': CountryLocationConfig(
        region_label='State',
        subregion_label='County',
        regions=['Alabama', 'Alaska', 'Arizona', 'Arkansas', 'California', 'Colorado', 'Connecticut', 'Delaware', 'Florida', 'Georgia', 'Hawaii', 'Idaho', 'Illinois', 'Indiana', 'Iowa', 'Kansas', 'Kentucky', 'Louisiana', 'Maine', 'Maryland', 'Massachusetts', 'Michigan', 'Minnesota', 'Mississippi', 'Missouri', 'Montana', 'Nebraska', 'Nevada', 'New Hampshire', 'New Jersey', 'New Mexico', 'New York', 'North Carolina', 'North Dakota', 'Ohio', 'Oklahoma', 'Oregon', 'Pennsylvania', 'Rhode Island', 'South Carolina', 'South Dakota', 'Tennessee', 'Texas', 'Utah', 'Vermont', 'Virginia', 'Washington', 'West Virginia', 'Wisconsin', 'Wyoming', 'American Samoa', 'District of Columbia', 'Guam', 'Northern Mariana Islands', 'Puerto Rico', 'United States Minor Outlying Islands', 'Virgin Islands, U.S.'],
        subregions={'California': ['Los Angeles County', 'Orange County', 'San Diego County', 'San Francisco County', 'Alameda County', 'Sacramento County'], 'New York': ['New York County', 'Kings County', 'Queens County', 'Bronx County', 'Richmond County', 'Suffolk County'], 'Texas': ['Harris County', 'Dallas County', 'Travis County', 'Bexar County', 'Tarrant County', 'Collin County'], 'Florida': ['Miami-Dade County', 'Broward County', 'Orange County', 'Palm Beach County', 'Hillsborough County'], 'Illinois': ['Cook County', 'DuPage County', 'Lake County']},
    ),
    'UY': CountryLocationConfig(
        region_label='Department',
        subregion_label='Municipality',
        regions=['Artigas', 'Canelones', 'Cerro Largo', 'Colonia', 'Durazno', 'Flores', 'Florida', 'Lavalleja', 'Maldonado', 'Montevideo', 'Paysandú', 'Río Negro', 'Rivera', 'Rocha', 'Salto', 'San José', 'Soriano', 'Tacuarembó', 'Treinta y Tres'],
        subregions={'Montevideo': ['Montevideo City', 'Las Piedras', 'Paysandú City'], 'Canelones': ['Las Piedras', 'Canelones City', 'La Paz', 'Santa Lucía'], 'Maldonado': ['Maldonado City', 'Punta del Este', 'San Carlos'], 'Salto': ['Salto City', 'Artigas City'], 'Colonia': ['Colonia del Sacramento', 'Mercedes', 'Carmelo']},
    ),
    'UZ': CountryLocationConfig(
        region_label='Region',
        subregion_label='District',
        regions=['Andijan Region', 'Bukhara Region', 'Fergana Region', 'Jizzakh Region', 'Karakalpakstan', 'Kashkadarya Region', 'Khorezm Region', 'Namangan Region', 'Navoiy Region', 'Samarkand Region', 'Sirdaryo Region', 'Surkhandarya Region', 'Tashkent City', 'Tashkent Region', 'Andijon', 'Buxoro', 'Farg‘ona', 'Jizzax', 'Namangan', 'Navoiy', 'Qashqadaryo', 'Qoraqalpog‘iston Respublikasi', 'Samarqand', 'Sirdaryo', 'Surxondaryo', 'Toshkent', 'Xorazm'],
        subregions={'Tashkent City': ['Tashkent City'], 'Tashkent Region': ['Angren', 'Chirchiq', 'Bekabad', 'Nurafshon'], 'Samarkand Region': ['Samarkand City', 'Kattakurgan', 'Urgut'], 'Fergana Region': ['Fergana City', 'Margilan', 'Quvasoy', 'Kokand'], 'Andijan Region': ['Andijan City', 'Asaka', 'Shahrixon'], 'Namangan Region': ['Namangan City', 'Kosonsoy', 'Pop', 'Uychi'], 'Bukhara Region': ['Bukhara City', 'Navoiy City', 'Qarshi']},
    ),
    'VA': CountryLocationConfig(
        region_label='State',
        subregion_label='Administrative Unit',
        regions=['Vatican City State'],
        subregions={'Vatican City State': ['Vatican City']},
    ),
    'VC': CountryLocationConfig(
        region_label='Parish',
        subregion_label='Village',
        regions=['Charlotte', 'Grenadines', 'Saint Andrew', 'Saint David', 'Saint George', 'Saint Patrick'],
        subregions={'Saint George': ['Kingstown'], 'Charlotte': ['Georgetown'], 'Grenadines': ['Port Elizabeth', 'Clifton'], 'Saint Patrick': ['Barrouallie'], 'Saint Andrew': ['Colonarie']},
    ),
    'VE': CountryLocationConfig(
        region_label='State',
        subregion_label='Municipality',
        regions=['Amazonas', 'Anzoátegui', 'Apure', 'Aragua', 'Barinas', 'Bolívar', 'Carabobo', 'Cojedes', 'Delta Amacuro', 'Dependencias Federales', 'Distrito Capital', 'Falcón', 'Guárico', 'Lara', 'Mérida', 'Miranda', 'Monagas', 'Nueva Esparta', 'Portuguesa', 'Sucre', 'Táchira', 'Trujillo', 'Vargas', 'Yaracuy', 'Zulia', 'La Guaira'],
        subregions={'Distrito Capital': ['Caracas City'], 'Miranda': ['Baruta', 'Chacao', 'El Hatillo', 'Sucre'], 'Zulia': ['Maracaibo', 'San Francisco', 'Cabimas', 'Ciudad Ojeda'], 'Carabobo': ['Valencia', 'Naguanagua', 'San Diego', 'Los Guayos'], 'Lara': ['Barquisimeto', 'Iribarren', 'Concepción', 'Jiménez'], 'Aragua': ['Maracay', 'Girardot', 'Zamora', 'Mario Briceño Iragorry'], 'Bolívar': ['Ciudad Bolívar', 'Caroní', 'Heres']},
    ),
    'VG': CountryLocationConfig(
        region_label='Territory',
        subregion_label='Locality',
        regions=['Virgin Islands, British'],
        subregions={},
    ),
    'VI': CountryLocationConfig(
        region_label='Territory',
        subregion_label='Locality',
        regions=['Virgin Islands, U.S.'],
        subregions={},
    ),
    'VN': CountryLocationConfig(
        region_label='Province',
        subregion_label='District',
        regions=['An Giang', 'Bà Rịa-Vũng Tàu', 'Bắc Giang', 'Bắc Kạn', 'Bạc Liêu', 'Bắc Ninh', 'Bến Tre', 'Bình Dương', 'Bình Định', 'Bình Phước', 'Bình Thuận', 'Cà Mau', 'Cần Thơ', 'Cao Bằng', 'Đà Nẵng', 'Đắk Lắk', 'Đắk Nông', 'Điện Biên', 'Đồng Nai', 'Đồng Tháp', 'Gia Lai', 'Hà Giang', 'Hà Nam', 'Hà Nội', 'Hà Tĩnh', 'Hải Dương', 'Hải Phòng', 'Hậu Giang', 'Hòa Bình', 'Hồ Chí Minh City', 'Hưng Yên', 'Khánh Hòa', 'Kiên Giang', 'Kon Tum', 'Lai Châu', 'Lâm Đồng', 'Lạng Sơn', 'Lào Cai', 'Long An', 'Nam Định', 'Nghệ An', 'Ninh Bình', 'Ninh Thuận', 'Phú Thọ', 'Phú Yên', 'Quảng Bình', 'Quảng Nam', 'Quảng Ngãi', 'Quảng Ninh', 'Quảng Trị', 'Sóc Trăng', 'Sơn La', 'Tây Ninh', 'Thái Bình', 'Thái Nguyên', 'Thanh Hóa', 'Thừa Thiên Huế', 'Tiền Giang', 'Trà Vinh', 'Tuyên Quang', 'Vĩnh Long', 'Vĩnh Phúc', 'Yên Bái', 'Hồ Chí Minh'],
        subregions={'Hà Nội': ['Ba Đình', 'Hoàn Kiếm', 'Đống Đa', 'Hai Bà Trưng', 'Cầu Giấy'], 'Hồ Chí Minh City': ['District 1', 'District 3', 'Bình Thạnh', 'Gò Vấp', 'Phú Nhuận'], 'Đà Nẵng': ['Hải Châu', 'Thanh Khê', 'Sơn Trà', 'Ngũ Hành Sơn'], 'Hải Phòng': ['Hồng Bàng', 'Ngô Quyền', 'Lê Chân', 'Kiến An'], 'Cần Thơ': ['Ninh Kiều', 'Bình Thủy', 'Cái Răng', 'Ô Môn'], 'Bình Dương': ['Thủ Dầu Một', 'Thuận An', 'Dĩ An', 'Bến Cát'], 'Đồng Nai': ['Biên Hòa', 'Long Khánh', 'Nhơn Trạch']},
    ),
    'VU': CountryLocationConfig(
        region_label='Province',
        subregion_label='Area',
        regions=['Malampa', 'Penama', 'Sanma', 'Shefa', 'Tafea', 'Torba'],
        subregions={'Shefa': ['Port Vila', 'Efate', 'Shepherd Islands'], 'Sanma': ['Luganville', 'Santo', 'Malo'], 'Malampa': ['Lakatoro', 'Malekula', 'Ambrym'], 'Tafea': ['Isangel', 'Tanna', 'Aniwa'], 'Penama': ['Saratamata', 'Ambae', 'Maewo', 'Pentecost'], 'Torba': ['Sola', 'Gaua', 'Torres Islands']},
    ),
    'WF': CountryLocationConfig(
        region_label='Region',
        subregion_label='District',
        regions=['Alo', 'Sigave', 'Uvea'],
        subregions={},
    ),
    'WS': CountryLocationConfig(
        region_label='District',
        subregion_label='Village',
        regions=["A'ana", 'Aiga-i-le-Tai', 'Atua', "Fa'asaleleaga", "Gaga'emauga", 'Gagaifomauga', 'Palauli', "Satupa'itea", 'Tuamasaga', "Va'a-o-Fonoti", 'Vaisigano'],
        subregions={'Tuamasaga': ['Apia', 'Faleula', 'Vailima'], "A'ana": ['Leulumoega', 'Nofoalii'], 'Atua': ['Lufilufi', 'Solosolo'], "Fa'asaleleaga": ['Saleologa', 'Lalomalava'], 'Palauli': ['Palauli', 'Samalaeulu']},
    ),
    'XK': CountryLocationConfig(
        region_label='District',
        subregion_label='Municipality',
        regions=['Pristina District', 'Prizren District', 'Peja District', 'Ferizaj District', 'Gjilan District', 'Gjakova District', 'Mitrovica District'],
        subregions={},
    ),
    'YE': CountryLocationConfig(
        region_label='Governorate',
        subregion_label='District',
        regions=['Abyan', 'Aden', 'Al Bayda', 'Al Hudaydah', 'Al Jawf', 'Al Mahrah', 'Al Mahwit', 'Amran', 'Dhamar', 'Hadhramaut', 'Hajjah', 'Ibb', 'Lahij', "Ma'rib", 'Raymah', "Sa'dah", "Sana'a", 'Socotra', 'Shabwah', 'Taizz', '‘Adan', 'Aḑ Ḑāli‘', 'Ḩaḑramawt', 'Amānat al ‘Āşimah [city]', 'Şanʻā’', 'Arkhabīl Suquţrá', 'Tāʻizz'],
        subregions={"Sana'a": ["Sana'a City", 'Bani Matar', 'Bani Hushaish', 'Hamdan'], 'Aden': ['Aden City', 'Crater', 'Khormaksar', 'Al Mualla'], 'Taizz': ['Taizz City', 'Al Mudhaffar', 'Al Qahirah'], 'Hadhramaut': ['Mukalla', "Say'un", 'Shibam'], 'Al Hudaydah': ['Hudaydah City', 'Zabid', 'Bayt al-Faqih'], 'Ibb': ['Ibb City', 'Dhamar City', 'Yarim']},
    ),
    'YT': CountryLocationConfig(
        region_label='Territory',
        subregion_label='Locality',
        regions=['Mayotte'],
        subregions={},
    ),
    'ZA': CountryLocationConfig(
        region_label='Province',
        subregion_label='Municipality',
        regions=['Gauteng', 'Western Cape', 'KwaZulu-Natal', 'Eastern Cape', 'Free State', 'Limpopo', 'Mpumalanga', 'Northern Cape', 'North-West'],
        subregions={},
    ),
    'ZM': CountryLocationConfig(
        region_label='Province',
        subregion_label='District',
        regions=['Lusaka', 'Copperbelt', 'Southern', 'Western', 'Central', 'Eastern', 'Luapula', 'Northern', 'North-Western', 'Muchinga'],
        subregions={},
    ),
    'ZW': CountryLocationConfig(
        region_label='Province',
        subregion_label='District',
        regions=['Harare', 'Bulawayo', 'Matabeleland North', 'Manicaland', 'Mashonaland Central', 'Mashonaland East', 'Midlands', 'Matabeleland South', 'Masvingo', 'Mashonaland West'],
        subregions={},
    ),
}

# ── Geographic groupings ─────────────────────────────────────────────────────
CONTINENT_CODES: Dict[str, List[str]] = {'Africa': ['DZ', 'AO', 'BJ', 'BW', 'BF', 'BI', 'CV', 'CM', 'CF', 'TD', 'KM', 'CG', 'CD', 'CI', 'DJ', 'EG', 'GQ', 'ER', 'SZ', 'ET', 'GA', 'GM', 'GH', 'GN', 'GW', 'KE', 'LS', 'LR', 'LY', 'MG', 'MW', 'ML', 'MR', 'MU', 'MA', 'MZ', 'NA', 'NE', 'NG', 'RW', 'ST', 'SN', 'SC', 'SL', 'SO', 'ZA', 'SS', 'SD', 'TZ', 'TG', 'TN', 'UG', 'ZM', 'ZW', 'EH', 'TF', 'RE', 'YT', 'SH', 'IO'], 'Europe': ['AL', 'AD', 'AT', 'BY', 'BE', 'BA', 'BG', 'HR', 'CY', 'CZ', 'DK', 'EE', 'FI', 'FR', 'DE', 'GR', 'HU', 'IS', 'IE', 'IT', 'XK', 'LV', 'LI', 'LT', 'LU', 'MT', 'MD', 'MC', 'ME', 'NL', 'MK', 'NO', 'PL', 'PT', 'RO', 'RU', 'SM', 'RS', 'SK', 'SI', 'ES', 'SE', 'CH', 'UA', 'GB', 'VA', 'AX', 'FO', 'GG', 'GI', 'GL', 'IM', 'JE', 'SJ'], 'Asia': ['AF', 'AM', 'AZ', 'BH', 'BD', 'BT', 'BN', 'KH', 'CN', 'GE', 'IN', 'ID', 'IR', 'IQ', 'IL', 'JP', 'JO', 'KZ', 'KW', 'KG', 'LA', 'LB', 'MY', 'MV', 'MN', 'MM', 'NP', 'KP', 'OM', 'PK', 'PH', 'QA', 'SA', 'SG', 'LK', 'SY', 'TW', 'TJ', 'TH', 'TL', 'TM', 'AE', 'UZ', 'VN', 'YE', 'HK', 'MO', 'KR', 'PS', 'TR'], 'North America': ['AG', 'BS', 'BB', 'BZ', 'CA', 'CR', 'CU', 'DM', 'DO', 'SV', 'GD', 'GT', 'HT', 'HN', 'JM', 'MX', 'NI', 'PA', 'KN', 'LC', 'VC', 'TT', 'US', 'AI', 'AS', 'AW', 'BL', 'BM', 'BQ', 'CC', 'CK', 'CW', 'CX', 'GU', 'KY', 'MP', 'PR', 'SX', 'TC', 'UM', 'VG', 'VI', 'GP', 'MQ', 'MF', 'PM', 'MS'], 'South America': ['AR', 'BO', 'BR', 'CL', 'CO', 'EC', 'GY', 'PY', 'PE', 'SR', 'UY', 'VE', 'FK', 'GF', 'GS'], 'Oceania': ['AU', 'FJ', 'KI', 'MH', 'FM', 'NR', 'NZ', 'PW', 'PG', 'WS', 'SB', 'TO', 'TV', 'VU', 'AQ', 'HM', 'NC', 'NF', 'NU', 'PF', 'PN', 'TK', 'WF'], 'Antarctica': ['BV']}
AFRICA_SUB_REGIONS: Dict[str, List[str]] = {'West Africa': ['NG', 'GH', 'SN', 'CI', 'ML', 'BF', 'GN', 'GW', 'LR', 'SL', 'MR', 'GM', 'CV', 'TG', 'BJ', 'NE'], 'East Africa': ['ET', 'KE', 'TZ', 'UG', 'RW', 'BI', 'DJ', 'ER', 'SO', 'SS'], 'North Africa': ['EG', 'LY', 'TN', 'DZ', 'MA', 'SD'], 'Central Africa': ['CD', 'CG', 'CM', 'CF', 'GA', 'GQ', 'ST', 'TD', 'AO'], 'Southern Africa': ['ZA', 'ZW', 'ZM', 'MW', 'MZ', 'NA', 'BW', 'LS', 'SZ', 'MG', 'MU', 'SC']}

WORLD_COUNTRY_COUNT = len(COUNTRY_NAMES)
ISO_COUNTRY_COUNT = 249
NON_ISO_COUNTRY_EXTENSIONS = ["XK"]

if WORLD_COUNTRY_COUNT != 250:
    raise RuntimeError(
        f"Unexpected world country catalogue size: {WORLD_COUNTRY_COUNT}; expected 250."
    )

if not set(COUNTRY_NAMES).issubset(LOCATION_CONFIG):
    missing = sorted(set(COUNTRY_NAMES) - set(LOCATION_CONFIG))
    raise RuntimeError(f"Countries missing LOCATION_CONFIG entries: {missing}")

if set(LOCATION_CONFIG) - set(COUNTRY_NAMES):
    extra = sorted(set(LOCATION_CONFIG) - set(COUNTRY_NAMES))
    raise RuntimeError(f"LOCATION_CONFIG contains unknown countries: {extra}")

for _code, _config in LOCATION_CONFIG.items():
    _regions = list(_config.regions)
    _region_norm = []
    for _region in _regions:
        _key = "".join(
            c for c in __import__("unicodedata").normalize("NFKD", str(_region))
            if __import__("unicodedata").category(c) != "Mn"
        )
        _key = _key.replace("’", "'").replace("‘", "'")
        _key = __import__("re").sub(r"[^A-Za-z0-9]+", " ", _key).strip().lower()
        _key = __import__("re").sub(r"\s+", " ", _key)
        _region_norm.append(_key)
    if len(_region_norm) != len(set(_region_norm)):
        raise RuntimeError(f"Duplicate regions for country {_code}.")
    _orphan_subregions = set(_config.subregions) - set(_regions)
    if _orphan_subregions:
        raise RuntimeError(
            f"Subregion parent(s) missing from region list for {_code}: "
            f"{sorted(_orphan_subregions)}"
        )
    for _parent, _children in _config.subregions.items():
        if len(_children) != len(set(_children)):
            raise RuntimeError(
                f"Duplicate subregions under {_code}/{_parent}."
            )

_continent_codes = [c for values in CONTINENT_CODES.values() for c in values]
if len(_continent_codes) != len(set(_continent_codes)):
    raise RuntimeError("Duplicate country code in CONTINENT_CODES.")
if set(_continent_codes) != set(COUNTRY_NAMES):
    raise RuntimeError(
        "CONTINENT_CODES must contain exactly the supported country catalogue."
    )

__all__ = [
    "CountryLocationConfig",
    "COUNTRY_NAMES",
    "LOCATION_CONFIG",
    "CONTINENT_CODES",
    "AFRICA_LOCATION_SEED",
    "AFRICA_SUB_REGIONS",
    "WORLD_COUNTRY_COUNT",
    "ISO_COUNTRY_COUNT",
    "NON_ISO_COUNTRY_EXTENSIONS",
]
