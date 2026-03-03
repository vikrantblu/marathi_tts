"""
Grapheme-to-Phoneme (G2P) Constants
====================================
Constants for the Marathi/Sanskrit G2P engine: schwa deletion rules,
conjunct cluster maps, anusvara context rules, visarga context rules,
and the exception lexicon.

Imports:
    from tts.constants.g2p_constants import (
        SCHWA_DELETE_SUFFIXES, SCHWA_PRESERVE_CLUSTERS,
        VALID_CONJUNCTS, ANUSVARA_ASSIMILATION,
        VISARGA_SANDHI_RULES, LOANWORD_PHONEMES,
        EXCEPTION_LEXICON,
    )
"""
from typing import Dict, List, Set, Tuple


# ═══════════════════════════════════════════════════════════════════════════
# DEVANAGARI CHARACTER CLASSES — used throughout G2P
# ═══════════════════════════════════════════════════════════════════════════

# Halant / virama
HALANT = '\u094D'

# Zero-width characters that affect conjunct rendering
ZWJ  = '\u200D'   # Zero Width Joiner — forces conjunct display
ZWNJ = '\u200C'   # Zero Width Non-Joiner — breaks conjunct

# Devanagari vowels (independent forms)
VOWELS: Set[str] = {
    'अ', 'आ', 'इ', 'ई', 'उ', 'ऊ', 'ऋ', 'ॠ',
    'ऌ', 'ॡ', 'ए', 'ऐ', 'ओ', 'औ',
}

# Devanagari matras (dependent vowel signs)
MATRAS: Set[str] = {
    'ा', 'ि', 'ी', 'ु', 'ू', 'ृ', 'ॄ',
    'ॢ', 'ॣ', 'े', 'ै', 'ो', 'ौ',
}

# Consonants by class (varga)
VELAR:       List[str] = ['क', 'ख', 'ग', 'घ', 'ङ']
PALATAL:     List[str] = ['च', 'छ', 'ज', 'झ', 'ञ']
RETROFLEX:   List[str] = ['ट', 'ठ', 'ड', 'ढ', 'ण']
DENTAL:      List[str] = ['त', 'थ', 'द', 'ध', 'न']
LABIAL:      List[str] = ['प', 'फ', 'ब', 'भ', 'म']
SEMIVOWELS:  List[str] = ['य', 'र', 'ल', 'व']
SIBILANTS:   List[str] = ['श', 'ष', 'स']
ASPIRATE:    List[str] = ['ह']
MARATHI_SPECIAL: List[str] = ['ळ']

ALL_CONSONANT_LIST: List[str] = (
    VELAR + PALATAL + RETROFLEX + DENTAL + LABIAL
    + SEMIVOWELS + SIBILANTS + ASPIRATE + MARATHI_SPECIAL
)

ALL_CONSONANT_SET: Set[str] = set(ALL_CONSONANT_LIST)

# Nasal for each varga (used by anusvara assimilation)
VARGA_NASAL: Dict[str, str] = {
    'क': 'ङ', 'ख': 'ङ', 'ग': 'ङ', 'घ': 'ङ', 'ङ': 'ङ',
    'च': 'ञ', 'छ': 'ञ', 'ज': 'ञ', 'झ': 'ञ', 'ञ': 'ञ',
    'ट': 'ण', 'ठ': 'ण', 'ड': 'ण', 'ढ': 'ण', 'ण': 'ण',
    'त': 'न', 'थ': 'न', 'द': 'न', 'ध': 'न', 'न': 'न',
    'प': 'म', 'फ': 'म', 'ब': 'म', 'भ': 'म', 'म': 'म',
}


# ═══════════════════════════════════════════════════════════════════════════
# SCHWA DELETION — Marathi-specific rules
# The implicit 'a' (schwa) after a consonant is deleted in Marathi
# at word-final and certain word-medial positions, unlike Hindi.
# ═══════════════════════════════════════════════════════════════════════════

# Suffixes that trigger schwa deletion on the preceding stem consonant.
# e.g., कमल → "kamal" (not "kamala") because the word is stem-final.
SCHWA_DELETE_SUFFIXES: Set[str] = {
    'ा', 'ि', 'ी', 'ु', 'ू', 'े', 'ै', 'ो', 'ौ',
    'ं', 'ः', '्',
}

# Consonant clusters where the schwa between them must be PRESERVED.
# e.g., "कमल" → the 'a' between म and ल is preserved: "kamal"
# but "धर्म" → the cluster र्म keeps the 'a' before it: "dharma"
SCHWA_PRESERVE_CLUSTERS: Set[str] = {
    'क्ष', 'ज्ञ', 'त्र', 'श्र', 'द्य', 'न्य', 'स्थ',
    'ष्ट', 'त्त', 'द्ध', 'न्न', 'स्त', 'स्न', 'श्व',
    'ध्य', 'भ्य', 'म्ह', 'ल्ह', 'न्ह', 'प्र', 'क्र',
    'ग्र', 'द्र', 'ब्र', 'स्व', 'त्व', 'ध्व',
}

# Words where schwa deletion is IRREGULAR (exceptions).
# Key = written form, Value = phonemic form with correct schwa.
# These entries also serve as a high-frequency bypass: words found here
# skip rule-based schwa processing, preventing over-application.
SCHWA_EXCEPTIONS: Dict[str, str] = {
    # ── Original handful ─────────────────────────────────────────────
    'कमल': 'कमल',     # kamal  (delete final)
    'नगर': 'नगर',     # nagar
    'समय': 'समय',     # samay
    'मनोहर': 'मनोहर', # manohar
    'दिवस': 'दिवस',   # divas
    'सुंदर': 'सुंदर',  # sundar
    'अमर': 'अमर',     # amar
    'प्रकार': 'प्रकार', # prakaar

    # ── Verb forms ending in -तो (masculine singular present) ────────
    # Schwa before -तो is deleted: बोल+तो → bolt-o, NOT bola-to
    'बोलतो': 'बोलतो',     # speaks     (bol-to)
    'करतो': 'करतो',       # does       (kar-to)
    'सांगतो': 'सांगतो',   # tells      (saang-to)
    'जातो': 'जातो',       # goes       (ja-to)
    'येतो': 'येतो',       # comes      (ye-to)
    'पाहतो': 'पाहतो',     # sees       (paa-h-to)
    'घेतो': 'घेतो',       # takes      (ghe-to)
    'देतो': 'देतो',       # gives      (de-to)
    'खातो': 'खातो',       # eats       (kha-to)
    'पितो': 'पितो',       # drinks     (pi-to)
    'हसतो': 'हसतो',       # laughs     (has-to)
    'रडतो': 'रडतो',       # cries      (rad-to)
    'धावतो': 'धावतो',     # runs       (dhaav-to)
    'खेळतो': 'खेळतो',     # plays      (kheL-to)
    'वाचतो': 'वाचतो',     # reads      (vaach-to)
    'लिहितो': 'लिहितो',   # writes     (lihi-to)
    'मागतो': 'मागतो',     # asks/begs  (maag-to)
    'काढतो': 'काढतो',     # takes out  (kaaDh-to)
    'निघतो': 'निघतो',     # leaves     (nigh-to)
    'बसतो': 'बसतो',       # sits       (bas-to)
    'उठतो': 'उठतो',       # gets up    (uTh-to)
    'झोपतो': 'झोपतो',     # sleeps     (jhop-to)
    'कळतो': 'कळतो',       # understands(kaL-to)
    'वळतो': 'वळतो',       # turns      (vaL-to)
    'मिळतो': 'मिळतो',     # gets       (miL-to)
    'चालतो': 'चालतो',     # walks/works(chaal-to)
    'पडतो': 'पडतो',       # falls      (paD-to)
    'उडतो': 'उडतो',       # flies      (uD-to)
    'तुटतो': 'तुटतो',     # breaks     (tuT-to)
    'फुटतो': 'फुटतो',     # bursts     (phuT-to)
    'सुटतो': 'सुटतो',     # escapes    (suT-to)

    # ── Verb forms ending in -ते (feminine singular present) ─────────
    'बोलते': 'बोलते',
    'करते': 'करते',
    'सांगते': 'सांगते',
    'जाते': 'जाते',
    'येते': 'येते',
    'पाहते': 'पाहते',
    'घेते': 'घेते',
    'देते': 'देते',
    'खाते': 'खाते',
    'हसते': 'हसते',
    'धावते': 'धावते',
    'खेळते': 'खेळते',
    'वाचते': 'वाचते',
    'लिहिते': 'लिहिते',
    'चालते': 'चालते',
    'पडते': 'पडते',
    'मिळते': 'मिळते',

    # ── Verb infinitives ending in -णे ───────────────────────────────
    'बोलणे': 'बोलणे',
    'करणे': 'करणे',
    'सांगणे': 'सांगणे',
    'जाणे': 'जाणे',
    'येणे': 'येणे',
    'पाहणे': 'पाहणे',
    'घेणे': 'घेणे',
    'देणे': 'देणे',
    'खाणे': 'खाणे',
    'पिणे': 'पिणे',
    'हसणे': 'हसणे',
    'रडणे': 'रडणे',
    'धावणे': 'धावणे',
    'खेळणे': 'खेळणे',
    'वाचणे': 'वाचणे',
    'लिहिणे': 'लिहिणे',
    'मागणे': 'मागणे',
    'शिकणे': 'शिकणे',
    'शिकवणे': 'शिकवणे',
    'दाखवणे': 'दाखवणे',
    'सांभाळणे': 'सांभाळणे',
    'ओळखणे': 'ओळखणे',
    'समजणे': 'समजणे',
    'विचारणे': 'विचारणे',
    'विसरणे': 'विसरणे',
    'समजावणे': 'समजावणे',

    # ── -कर suffix compounds (agent nouns, demonyms) ─────────────────
    # Last syllable schwa of stem is kept; only word-final schwa deleted
    'शेतकरी': 'शेतकरी',   # farmer     (shet-ka-ri)
    'पुणेकर': 'पुणेकर',   # Pune-dweller
    'मुंबईकर': 'मुंबईकर', # Mumbai-dweller
    'नागपूरकर': 'नागपूरकर',
    'नाशिककर': 'नाशिककर',
    'औरंगाबादकर': 'औरंगाबादकर',
    'कोल्हापूरकर': 'कोल्हापूरकर',
    'दिल्लीकर': 'दिल्लीकर',
    'ग्रामकर': 'ग्रामकर',
    'मजूर': 'मजूर',       # labourer
    'सरकार': 'सरकार',     # government (sar-kaar)
    'व्यापार': 'व्यापार', # trade

    # ── Common adjectives ─────────────────────────────────────────────
    'चांगला': 'चांगला',   # good (chaaNG-la)
    'चांगली': 'चांगली',
    'चांगले': 'चांगले',
    'मोठा': 'मोठा',       # big
    'मोठी': 'मोठी',
    'मोठे': 'मोठे',
    'छोटा': 'छोटा',       # small
    'छोटी': 'छोटी',
    'लहान': 'लहान',       # small/young
    'जड': 'जड',           # heavy
    'हलका': 'हलका',       # light
    'कठीण': 'कठीण',       # difficult
    'सोपा': 'सोपा',       # easy
    'सोपी': 'सोपी',
    'नवीन': 'नवीन',       # new
    'जुना': 'जुना',       # old
    'जुनी': 'जुनी',
    'गरम': 'गरम',         # hot
    'थंड': 'थंड',         # cold
    'ओला': 'ओला',         # wet
    'कोरडा': 'कोरडा',     # dry
    'गोड': 'गोड',         # sweet
    'कडू': 'कडू',         # bitter
    'खारट': 'खारट',       # salty
    'आंबट': 'आंबट',       # sour
    'तिखट': 'तिखट',       # spicy
    'खरा': 'खरा',         # true/real
    'खोटा': 'खोटा',       # false
    'श्रीमंत': 'श्रीमंत', # rich
    'गरीब': 'गरीब',       # poor
    'शहाणा': 'शहाणा',     # wise/clever

    # ── Common nouns ──────────────────────────────────────────────────
    'जीवन': 'जीवन',       # life
    'मन': 'मन',           # mind/heart
    'तन': 'तन',           # body
    'धन': 'धन',           # wealth
    'चरण': 'चरण',         # feet (respectful)
    'भवन': 'भवन',         # building
    'वचन': 'वचन',         # word/promise
    'स्मरण': 'स्मरण',     # remembrance
    'लक्षण': 'लक्षण',     # sign/symptom
    'कारण': 'कारण',       # reason
    'साधन': 'साधन',       # means/tool
    'वर्तन': 'वर्तन',     # behaviour
    'श्रवण': 'श्रवण',     # hearing
    'दर्शन': 'दर्शन',     # vision/sight
    'भजन': 'भजन',         # devotional song
    'कीर्तन': 'कीर्तन',   # devotional singing
    'पवन': 'पवन',         # wind
    'नयन': 'नयन',         # eyes (Sanskrit)
    'शरण': 'शरण',         # refuge
    'घर': 'घर',           # house
    'दुकान': 'दुकान',     # shop
    'बाजार': 'बाजार',     # market
    'शाळा': 'शाळा',       # school
    'महाविद्यालय': 'महाविद्यालय', # college
    'रुग्णालय': 'रुग्णालय', # hospital
    'देश': 'देश',         # country
    'गाव': 'गाव',         # village
    'शहर': 'शहर',         # city
    'रस्ता': 'रस्ता',     # road
    'पाणी': 'पाणी',       # water
    'अन्न': 'अन्न',       # food
    'भात': 'भात',         # rice
    'पोळी': 'पोळी',       # flatbread

    # ── Place names ───────────────────────────────────────────────────
    'पुणे': 'पुणे',
    'मुंबई': 'मुंबई',
    'नागपूर': 'नागपूर',
    'औरंगाबाद': 'औरंगाबाद',
    'नाशिक': 'नाशिक',
    'कोल्हापूर': 'कोल्हापूर',
    'सातारा': 'सातारा',
    'सोलापूर': 'सोलापूर',
    'ठाणे': 'ठाणे',
    'पनवेल': 'पनवेल',
    'महाराष्ट्र': 'महाराष्ट्र',
    'भारत': 'भारत',
    'पंढरपूर': 'पंढरपूर',   # pilgrim city
    'अलंदी': 'अलंदी',       # Sant Dnyaneshwar's samadhi
    'देहू': 'देहू',           # Sant Tukaram's village

    # ── Common adverbs and particles ──────────────────────────────────
    'आता': 'आता',         # now
    'तेव्हा': 'तेव्हा',   # then
    'नंतर': 'नंतर',       # later
    'आधी': 'आधी',         # before
    'मग': 'मग',           # then/after
    'पण': 'पण',           # but
    'म्हणून': 'म्हणून',   # therefore
    'कारण': 'कारण',       # because/reason
    'फक्त': 'फक्त',       # only
    'अजून': 'अजून',       # still/yet
    'नेहमी': 'नेहमी',     # always
    'कधी': 'कधी',         # when/ever
    'कोठे': 'कोठे',       # where
    'कसे': 'कसे',         # how
    'किती': 'किती',       # how much/many
    'इथे': 'इथे',         # here
    'तिथे': 'तिथे',       # there
    'वर': 'वर',           # on/up
    'खाली': 'खाली',       # down/below
    'आत': 'आत',           # inside
    'बाहेर': 'बाहेर',     # outside
    'पुढे': 'पुढे',       # ahead
    'मागे': 'मागे',       # behind
    'जवळ': 'जवळ',         # near
    'दूर': 'दूर',         # far
    'लवकर': 'लवकर',       # soon/early
    'उशिरा': 'उशिरा',     # late

    # ── Postpositions (vibhakti) ──────────────────────────────────────
    'बद्दल': 'बद्दल',     # about/regarding
    'साठी': 'साठी',       # for
    'मुळे': 'मुळे',       # because of  ← retroflex ळ
    'शिवाय': 'शिवाय',     # without
    'सारखा': 'सारखा',     # like/similar
    'पेक्षा': 'पेक्षा',   # than
    'प्रमाणे': 'प्रमाणे', # according to
    'द्वारे': 'द्वारे',   # via/through

    # ── Common person/relationship words ─────────────────────────────
    'आई': 'आई',           # mother
    'बाबा': 'बाबा',       # father
    'दादा': 'दादा',       # elder brother
    'ताई': 'ताई',         # elder sister
    'भाऊ': 'भाऊ',         # brother
    'आजी': 'आजी',         # grandmother
    'आजोबा': 'आजोबा',     # grandfather
    'काका': 'काका',       # uncle (father's brother)
    'काकी': 'काकी',       # aunt
    'मामा': 'मामा',       # maternal uncle
    'मुलगा': 'मुलगा',     # son/boy
    'मुलगी': 'मुलगी',     # daughter/girl
    'मित्र': 'मित्र',     # friend (m)
    'मैत्रीण': 'मैत्रीण', # friend (f)
    'शिक्षक': 'शिक्षक',   # teacher (m)
    'शिक्षिका': 'शिक्षिका', # teacher (f)

    # ── Bhakti / spiritual vocabulary ────────────────────────────────
    'विठोबा': 'विठोबा',
    'माउली': 'माउली',     # mother (affectionate for Dnyaneshwar)
    'पांडुरंग': 'पांडुरंग',
    'वारकरी': 'वारकरी',
    'वारी': 'वारी',
    'भक्त': 'भक्त',
    'संत': 'संत',
    'पुजारी': 'पुजारी',
    'देऊळ': 'देऊळ',       # temple (Marathi; retroflex ळ)
    'मंदिर': 'मंदिर',     # temple (Sanskrit)
    'उपवास': 'उपवास',     # fast
    'प्रसाद': 'प्रसाद',   # blessed food
    'तीर्थ': 'तीर्थ',     # pilgrimage / holy water
    'यात्रा': 'यात्रा',   # pilgrimage
    'अष्टमी': 'अष्टमी',   # eighth day
    'एकादशी': 'एकादशी',   # eleventh day
}


# ═══════════════════════════════════════════════════════════════════════════
# VALID CONJUNCTS — Consonant clusters that must be PRESERVED as units.
# The G2P must NOT break these apart or drop any component.
# Map: written conjunct → phonetic description (for debugging).
# ═══════════════════════════════════════════════════════════════════════════

VALID_CONJUNCTS: Dict[str, str] = {
    # Conjuncts with य (the ones being dropped — ROOT CAUSE of च्या→चा)
    'च्य': 'cha+ya',   'ज्य': 'ja+ya',    'झ्य': 'jha+ya',
    'ट्य': 'ṭa+ya',    'ठ्य': 'ṭha+ya',   'ड्य': 'ḍa+ya',
    'त्य': 'ta+ya',    'द्य': 'da+ya',    'ध्य': 'dha+ya',
    'न्य': 'na+ya',    'प्य': 'pa+ya',    'ब्य': 'ba+ya',
    'भ्य': 'bha+ya',   'म्य': 'ma+ya',    'व्य': 'va+ya',
    'श्य': 'sha+ya',   'स्य': 'sa+ya',    'ल्य': 'la+ya',
    'ख्य': 'kha+ya',   'ग्य': 'ga+ya',    'क्य': 'ka+ya',
    'र्य': 'ra+ya',

    # Conjuncts with र
    'प्र': 'pra',  'क्र': 'kra',  'ग्र': 'gra',  'त्र': 'tra',
    'द्र': 'dra',  'ब्र': 'bra',  'श्र': 'shra', 'ध्र': 'dhra',
    'भ्र': 'bhra', 'स्र': 'sra',

    # Conjuncts with व
    'त्व': 'tva',  'द्व': 'dva',  'स्व': 'sva',  'ध्व': 'dhva',
    'श्व': 'shva',

    # Conjuncts with ह (Marathi म्ह, ल्ह, न्ह)
    'म्ह': 'mha',  'ल्ह': 'lha',  'न्ह': 'nha',  'प्ह': 'pha',

    # Common double consonants / geminates
    'क्क': 'kka',  'ग्ग': 'gga',  'च्च': 'chcha', 'ज्ज': 'jja',
    'ट्ट': 'ṭṭa',  'ड्ड': 'ḍḍa',  'त्त': 'tta',   'द्द': 'dda',
    'प्प': 'ppa',  'ब्ब': 'bba',  'न्न': 'nna',   'म्म': 'mma',
    'ल्ल': 'lla',  'स्स': 'ssa',

    # Special conjuncts
    'क्ष': 'ksha', 'ज्ञ': 'dnya', 'द्ध': 'ddha', 'ष्ट': 'shṭa',
    'ष्ठ': 'shṭha', 'स्थ': 'stha', 'स्त': 'sta',  'स्न': 'sna',
    'स्म': 'sma',  'श्न': 'shna', 'ण्ड': 'ṇḍa',  'ण्ढ': 'ṇḍha',
    'ण्य': 'ṇya',  'ळ्य': 'Lya',

    # Retroflex + ர conjuncts
    'ड्र': 'ḍra',  'ट्र': 'ṭra',
}


# ═══════════════════════════════════════════════════════════════════════════
# ANUSVARA (ं) ASSIMILATION RULES
# The anusvara is NOT a single phoneme — it assimilates to the varga
# nasal of the FOLLOWING consonant. This map provides the phonetic
# realization based on the next consonant.
#
# Rule: anusvara + consonant → varga_nasal + consonant
# e.g., पंख → पङ्ख,  संत → सन्त,  गंभीर → गम्भीर
#
# Special: Before य, र, ल, व, श, ष, स, ह → nasalization of
# PRECEDING vowel (no stop insertion). Do NOT insert न्.
# ═══════════════════════════════════════════════════════════════════════════

ANUSVARA_ASSIMILATION: Dict[str, str] = {
    # Velar class (anusvara → ङ)
    'क': 'ङ्', 'ख': 'ङ्', 'ग': 'ङ्', 'घ': 'ङ्',
    # Palatal class (anusvara → ञ)
    'च': 'ञ्', 'छ': 'ञ्', 'ज': 'ञ्', 'झ': 'ञ्',
    # Retroflex class (anusvara → ण)
    'ट': 'ण्', 'ठ': 'ण्', 'ड': 'ण्', 'ढ': 'ण्',
    # Dental class (anusvara → न)
    'त': 'न्', 'थ': 'न्', 'द': 'न्', 'ध': 'न्', 'न': 'न्',
    # Labial class (anusvara → म)
    'प': 'म्', 'फ': 'म्', 'ब': 'म्', 'भ': 'म्', 'म': 'म्',
}

# Consonants before which anusvara is just vowel nasalization
# (do NOT replace with any stop nasal)
ANUSVARA_NASALIZE_ONLY: Set[str] = {
    'य', 'र', 'ल', 'व', 'श', 'ष', 'स', 'ह',
}


# ═══════════════════════════════════════════════════════════════════════════
# VISARGA (ः) SANDHI RULES — Context-dependent pronunciation
# The visarga echoes the preceding vowel OR becomes a sibilant before
# certain consonants. It is NOT a simple 'ha' replacement.
# ═══════════════════════════════════════════════════════════════════════════

# Before these consonant classes, visarga → sibilant
VISARGA_TO_SIBILANT: Dict[str, str] = {
    # Before palatal consonants → श (palatal sibilant)
    'च': 'श्', 'छ': 'श्',
    # Before retroflex consonants → ष (retroflex sibilant)
    'ट': 'ष्', 'ठ': 'ष्',
    # Before dental consonants → स (dental sibilant)
    'त': 'स्', 'थ': 'स्',
    # Before sibilants → assimilate to that sibilant
    'श': 'श्', 'ष': 'ष्', 'स': 'स्',
}

# Vowels and what the visarga echo sounds like after them
# e.g., रामः before pause → "raamaha"
# e.g., देवः before pause → "devaha"
VISARGA_ECHO: Dict[str, str] = {
    'अ': 'ह',   # अः → अह
    'आ': 'ह',   # आः → आह
    'इ': 'हि',  # इः → इहि
    'ई': 'ही',  # produces echo of the vowel
    'उ': 'हु',
    'ऊ': 'हू',
    'ए': 'हे',
    'ऐ': 'है',
}

# Specific visarga words that are EXCEPTIONS to the above rules
# (hard-coded pronunciations from usage)
VISARGA_EXCEPTIONS: Dict[str, str] = {
    'दुःख': 'दुख्ख',
    'दुःखी': 'दुख्खी',
    'दुःखद': 'दुख्खद',
    'नमः': 'नमहा',
    'स्वतः': 'स्वतह',
    'स्वत:': 'स्वतह',
    'मनःपूर्वक': 'मनःपूर्वक',
    'मनःस्थिती': 'मनःस्थिती',
    'अंतःकरण': 'अंतःकरण',
    'पुनः': 'पुनहा',
    'प्रातः': 'प्रातःकाळ',
    'अतः': 'अतहा',
    'ततः': 'ततहा',
}


# ═══════════════════════════════════════════════════════════════════════════
# LOANWORD PHONEMES — English words written in Devanagari
# Need special handling because standard G2P rules don't apply.
# ═══════════════════════════════════════════════════════════════════════════

LOANWORD_PHONEMES: Dict[str, str] = {
    'बँक': 'बॅंक',
    'डॉक्टर': 'डॉक्टर',
    'कॉम्प्युटर': 'कॉम्प्युटर',
    'इंजिनीअर': 'इंजिनीअर',
    'टेलिफोन': 'टेलिफोन',
    'मोबाईल': 'मोबाईल',
    'इंटरनेट': 'इंटरनेट',
    'ऑनलाइन': 'ऑनलाइन',
    'बस': 'बस',
    'ट्रेन': 'ट्रेन',
    'स्कूल': 'स्कूल',
    'हॉस्पिटल': 'हॉस्पिटल',
    'पोलीस': 'पोलीस',
    'स्टेशन': 'स्टेशन',
}


# ═══════════════════════════════════════════════════════════════════════════
# EXCEPTION LEXICON — Words with irregular pronunciation.
# Key: written form, Value: pronunciation override.
# This lexicon is checked BEFORE rule-based G2P runs.
# ═══════════════════════════════════════════════════════════════════════════

EXCEPTION_LEXICON: Dict[str, str] = {
    # Conjunct mispronunciations (the core bugs)
    'च्या': 'च्या',        # MUST keep the य — NOT चा
    'झ्या': 'झ्या',        # MUST keep the य
    'ज्या': 'ज्या',
    'त्या': 'त्या',
    'ध्या': 'ध्या',
    'न्या': 'न्या',
    'व्या': 'व्या',
    'श्या': 'श्या',
    'स्या': 'स्या',
    'ल्या': 'ल्या',
    'भ्या': 'भ्या',
    'म्या': 'म्या',
    'प्या': 'प्या',
    'क्या': 'क्या',
    'ठ्या': 'ठ्या',
    'ड्या': 'ड्या',

    # ये suffixed forms
    'मध्ये': 'मध्ये',
    'च्यात': 'च्यात',
    'त्यांना': 'त्यांना',
    'त्यांनी': 'त्यांनी',
    'त्यांचे': 'त्यांचे',

    # Corrected conjuncts
    'बुद्धी': 'बुद्धी',
    'बुद्ध': 'बुद्ध',
    'शुद्ध': 'शुद्ध',
    'वृद्ध': 'वृद्ध',
    'विद्यार्थी': 'विद्यार्थी',

    # Retroflex ळ words
    'मुळे': 'मुळे',
    'प्रमाणे': 'प्रमाणे',
    'कोळसा': 'कोळसा',
    'बाळ': 'बाळ',
    'काळ': 'काळ',
    'वेळ': 'वेळ',
    'जवळ': 'जवळ',
    'फळ': 'फळ',
    'तळ': 'तळ',
    'पाळणा': 'पाळणा',
    'कळणे': 'कळणे',

    # Anusvara words — preserve nasalization
    'पदरीं': 'पदरी',      # Nasalized ी at end → plain ी
    'श्रीचरणीं': 'श्रीचरणी',
    'स्मरणीं': 'स्मरणी',
    'मनीं': 'मनी',
    'ध्यानीं': 'ध्यानी',
    'कानीं': 'कानी',
    'हातीं': 'हाती',
    'पायीं': 'पायी',
    'कीर्तनीं': 'कीर्तनी',
    'शरणीं': 'शरणी',

    # Common pronunciation shifts
    # NOTE: 'मध्ये' is standard — do NOT simplify
    'मधील': 'मधल',
    'डोळ्यांत': 'डोळ्यात',

    # ═══════════════════════════════════════════════════════════════════
    # SANSKRIT DEITY NAMES & STOTRA VOCABULARY
    # These are tatsama words where gTTS (trained on modern Marathi) gets
    # the stress, length, or conjunct wrong.
    # ═══════════════════════════════════════════════════════════════════

    # God names & epithets
    'गणेश':       'गणेश',
    'गणपती':      'गणपती',
    'विघ्नहर्ता':   'विघ्नहर्ता',
    'गणाधीश':     'गणाधीश',
    'विनायक':     'विनायक',
    'लंबोदर':     'लंबोदर',
    'हेरंब':       'हेरंब',
    'एकदंत':      'एकदंत',
    'विघ्नराज':    'विघ्नराज',
    'शिव':         'शिव',
    'शिवाय':      'शिवाय',
    'शंकर':        'शंकर',
    'महादेव':     'महादेव',
    'शूलपाणी':    'शूलपाणी',
    'त्रिलोचन':    'त्रिलोचन',
    'त्र्यंबक':     'त्र्यंबक',
    'नीलकंठ':     'नीलकंठ',
    'पशुपती':     'पशुपती',
    'विष्णु':       'विष्णू',
    'विष्णू':       'विष्णू',
    'नारायण':     'नारायण',
    'वासुदेव':    'वासुदेव',
    'माधव':       'माधव',
    'केशव':        'केशव',
    'मुकुंद':      'मुकुंद',
    'हरि':          'हरि',
    'हरी':          'हरी',
    'विठ्ठल':      'विठ्ठल',
    'विठोबा':     'विठोबा',
    'पंढरीराया':   'पंढरीराया',
    'राम':          'राम',
    'रामा':         'रामा',
    'रामचंद्र':     'रामचंद्र',
    'दशरथ':       'दशरथ',
    'कृष्ण':       'कृष्ण',
    'कान्हा':      'कान्हा',
    'गोविंद':     'गोविंद',
    'गोपाल':      'गोपाल',
    'देवकीनंदन':  'देवकीनंदन',
    'मुरलीधर':    'मुरलीधर',
    'दुर्गा':        'दुर्गा',
    'अंबा':         'अंबा',
    'भवानी':      'भवानी',
    'जगदंबा':    'जगदंबा',
    'पार्वती':      'पार्वती',
    'सरस्वती':   'सरस्वती',
    'वाग्देवी':    'वाग्देवी',
    'लक्ष्मी':     'लक्ष्मी',
    'महालक्ष्मी':  'महालक्ष्मी',
    'त्रिपुरसुंदरी': 'त्रिपुरसुंदरी',
    'हनुमान':    'हनुमान',
    'मारुती':     'मारुती',
    'अंजनीसुत':  'अंजनीसुत',
    'रामदूत':     'रामदूत',
    'सूर्य':        'सूर्य',
    'सूर्यनारायण': 'सूर्यनारायण',
    'भास्कर':    'भास्कर',

    # Common stotra words
    'नमस्कार':   'नमस्कार',
    'प्रणाम':     'प्रणाम',
    'वंदन':        'वंदन',
    'स्तुती':       'स्तुती',
    'स्तोत्र':       'स्तोत्र',
    'मंत्र':         'मंत्र',
    'अनुष्ठान':   'अनुष्ठान',
    'आरती':       'आरती',
    'पूजा':         'पूजा',
    'अर्चना':      'अर्चना',
    'भजन':        'भजन',
    'प्रार्थना':    'प्रार्थना',
    'कीर्तन':      'कीर्तन',
    'अभंग':       'अभंग',

    # Sanskrit pronouns / particles (used in Sanskrit inserts in Marathi stotras)
    'यस्य':         'यस्य',
    'तस्य':         'तस्य',
    'येन':           'येन',
    'तेन':           'तेन',
    'यत्र':          'यत्र',
    'तत्र':          'तत्र',
    'यदा':          'यदा',
    'तदा':          'तदा',

    # ═══════════════════════════════════════════════════════════════════
    # SANT LITERATURE — HIGH FREQUENCY ABHANGA / OVI WORDS
    # ═══════════════════════════════════════════════════════════════════
    'तुका':         'तुका',           # Tukaram
    'तुकाराम':     'तुकाराम',
    'ज्ञानदेव':    'दनदेव',          # Dnyandev: ज्ञ → dn in Marathi
    'ज्ञानेश्वर':   'दनेश्वर',          # Dnyaneshwar
    'नामदेव':     'नामदेव',
    'एकनाथ':     'एकनाथ',
    'पंढरी':       'पंढरी',
    'पंढरपूर':    'पंढरपूर',
    'वारी':          'वारी',
    'वारकरी':    'वारकरी',
    'भक्त':         'भक्त',
    'भक्ती':        'भक्ती',
    'आनंद':       'आनंद',
    'सुख':           'सुख',
    'दुःख':          'दुःख',
    'मोक्ष':         'मोक्ष',
    'ध्यान':         'ध्यान',
    'धन':            'धन',
    'संसार':        'संसार',
    'माया':          'माया',
    'ब्रह्म':          'ब्रह्म',
    'ब्रह्मानंद':    'ब्रह्मानंद',
    'परमार्थ':      'परमार्थ',
    'सत्य':          'सत्य',
    'अमृत':        'अमृत',

    # ═══════════════════════════════════════════════════════════════════
    # COMMON MARATHI WORD-PRONUNCIATION FIXES
    # Words gTTS consistently gets wrong
    # ═══════════════════════════════════════════════════════════════════
    'प्रश्न':         'प्रश्न',
    'कवठ':          'कवट',          # dialectal form
    'ब्राह्मण':       'ब्राह्मण',
    'सत्संग':        'सत्संग',
    'सज्जन':        'सज्जन',
    'दुर्जन':         'दुर्जन',
    'उत्सव':         'उत्सव',
    'महोत्सव':     'महोत्सव',
    'समाधान':    'समाधान',
    'निवृत्ती':      'निवृत्ती',
    'प्रवृत्ती':       'प्रवृत्ती',
}
