"""Greek→Romanian and Hebrew→Romanian biblical lexicon for scan output.

Chain: manuscript form → lemma (MorphGNT) → Romanian (manual dict) or English (Strong's).
Strong's Concordance (1890) is public domain.
"""

import os
import json

# Load dictionaries (priority: manual RO → Strong's RO → Strong's EN)
_LEXICON_RO_PATH = os.path.join(os.path.dirname(__file__), 'lexicon_ro.json')
_STRONGS_RO_PATH = os.path.join(os.path.dirname(__file__), 'strongs_ro.json')
_STRONGS_EN_PATH = os.path.join(os.path.dirname(__file__), 'strongs_greek.json')
_LEXICON_RO = {}
_STRONGS_RO = {}
_STRONGS_EN = {}
if os.path.exists(_LEXICON_RO_PATH):
    with open(_LEXICON_RO_PATH, 'r', encoding='utf-8') as f:
        _LEXICON_RO = json.load(f)
if os.path.exists(_STRONGS_RO_PATH):
    with open(_STRONGS_RO_PATH, 'r', encoding='utf-8') as f:
        _STRONGS_RO = json.load(f)
if os.path.exists(_STRONGS_EN_PATH):
    with open(_STRONGS_EN_PATH, 'r', encoding='utf-8') as f:
        _STRONGS_EN = json.load(f)

# Greek NT → Romanian (common words)
GREEK_RO = {
    # Dumnezeu, Iisus, persoane
    'θεός': 'Dumnezeu', 'θεοῦ': 'lui Dumnezeu', 'θεῷ': 'lui Dumnezeu',
    'θεόν': 'pe Dumnezeu',
    'Ἰησοῦς': 'Iisus', 'Ἰησοῦ': 'lui Iisus', 'Ἰησοῦν': 'pe Iisus',
    'Χριστός': 'Hristos', 'Χριστοῦ': 'lui Hristos', 'Χριστόν': 'pe Hristos',
    'κύριος': 'Domn', 'κυρίου': 'Domnului', 'κυρίῳ': 'Domnului',
    'πατήρ': 'Tată', 'πατρός': 'Tatălui', 'πατέρα': 'pe Tatăl',
    'υἱός': 'Fiu', 'υἱοῦ': 'Fiului', 'υἱόν': 'pe Fiul',
    'πνεῦμα': 'Duh', 'πνεύματος': 'Duhului',
    'Μωϋσῆς': 'Moise', 'Ἀβραάμ': 'Avraam', 'Δαυίδ': 'David',
    'Πέτρος': 'Petru', 'Παῦλος': 'Pavel',
    'Μαρία': 'Maria', 'Μαρίας': 'Mariei', 'Μαριάμ': 'Maria',
    'Μάρθα': 'Marta', 'Λάζαρος': 'Lazăr', 'Λάζαρε': 'Lazăre',
    'Σατανᾶς': 'Satana', 'Πιλᾶτος': 'Pilat',
    # Concepte teologice
    'ἀγάπη': 'dragoste', 'ἀγάπην': 'dragoste',
    'πίστις': 'credință', 'πίστιν': 'credință', 'πίστεως': 'credinței',
    'ἐλπίς': 'nădejde', 'χάρις': 'har', 'χάριτος': 'harului',
    'εἰρήνη': 'pace', 'εἰρήνην': 'pace',
    'ἀλήθεια': 'adevăr', 'ἀληθείας': 'adevărului',
    'δόξα': 'slavă', 'δόξαν': 'slavă', 'δόξης': 'slavei',
    'ζωή': 'viață', 'ζωήν': 'viață', 'ζωῆς': 'vieții',
    'θάνατος': 'moarte', 'θανάτου': 'morții',
    'ἀνάστασις': 'înviere', 'ἀναστάσει': 'înviere',
    'σωτηρία': 'mântuire', 'σωτηρίαν': 'mântuire',
    'κρίσις': 'judecată', 'κρίσιν': 'judecată',
    'βασιλεία': 'împărăție', 'βασιλείαν': 'împărăție',
    'ἁμαρτία': 'păcat', 'ἁμαρτίας': 'păcatului',
    'μαρτυρία': 'mărturie', 'μαρτυρίαν': 'mărturie',
    'σημεῖον': 'semn', 'σημεῖα': 'semne',
    # Cuvânt, lumină
    'λόγος': 'Cuvânt', 'λόγον': 'cuvânt', 'λόγου': 'cuvântului',
    'φῶς': 'lumină', 'φωτός': 'luminii',
    'σκοτία': 'întuneric', 'σκότος': 'întuneric',
    # Trup, sânge, apă, pâine, vin
    'σάρξ': 'trup', 'σαρκός': 'trupului',
    'αἷμα': 'sânge', 'αἵματος': 'sângelui',
    'ὕδωρ': 'apă', 'ὕδατος': 'apei',
    'ἄρτος': 'pâine', 'ἄρτον': 'pâine', 'ἄρτους': 'pâini',
    'οἶνος': 'vin', 'οἶνον': 'vin',
    # Persoane, grupuri
    'ἄνθρωπος': 'om', 'ἀνθρώπου': 'omului', 'ἄνθρωπον': 'pe om',
    'μαθητής': 'ucenic', 'μαθηταί': 'ucenicii',
    'ἀπόστολος': 'apostol', 'προφήτης': 'profet',
    'ἱερεύς': 'preot', 'ἀρχιερεύς': 'arhiereu',
    'ἄγγελος': 'înger', 'ἀγγέλων': 'îngerilor',
    'δοῦλος': 'rob', 'δούλου': 'robului',
    'ἔθνος': 'neam', 'ἔθνη': 'neamuri',
    'ὄχλος': 'mulțime', 'ὄχλον': 'mulțime',
    'ἐκκλησία': 'biserică',
    # Locuri
    'κόσμος': 'lume', 'κόσμον': 'lume', 'κόσμου': 'lumii',
    'οὐρανός': 'cer', 'οὐρανοῦ': 'cerului',
    'γῆ': 'pământ', 'γῆς': 'pământului',
    'ναός': 'templu', 'ναοῦ': 'templului',
    'ἱερόν': 'templu',
    'σπήλαιον': 'peșteră',
    'Ἱεροσόλυμα': 'Ierusalim', 'Βηθανία': 'Betania',
    'Ναζαρέτ': 'Nazaret', 'Γαλιλαία': 'Galileea',
    'παράδεισος': 'rai', 'γέεννα': 'gheenă',
    # Obiecte, natură
    'τράπεζα': 'masă', 'τράπεζας': 'mese',
    'σταυρός': 'cruce', 'σταυρόν': 'cruce',
    'λίθος': 'piatră', 'λίθον': 'piatră',
    'μνημεῖον': 'mormânt', 'μνημεῖα': 'morminte',
    'βαΐα': 'ramuri finic', 'πῶλος': 'mânz', 'πῶλον': 'mânz',
    'ὄνος': 'asin', 'ὄνου': 'asinului',
    'περιστερά': 'porumbel', 'περιστεράς': 'porumbei',
    'ἀρνίον': 'miel', 'ἀρνίου': 'mielului',
    'σινδών': 'pânză', 'σινδόνα': 'pânza',
    'σουδάριον': 'mahramă', 'σουδαρίῳ': 'mahramă',
    'κειρία': 'fâșii', 'κειρίαις': 'fâșii',
    # Verbe frecvente (forme comune)
    'πιστεύω': 'cred', 'πιστεύων': 'cel ce crede',
    'πιστεύετε': 'credeți', 'πιστεύσητε': 'să credeți',
    'ἀγαπάω': 'iubesc', 'ἀγαπᾷ': 'iubește',
    'λύσατε': 'dezlegați', 'λύω': 'dezleg',
    'ἐγείρω': 'ridic/înviez', 'ἐγείρεται': 'se ridică',
    'Ὡσαννά': 'Osana', 'ἀμήν': 'amin',
    # Adjective, adverbe
    'ἅγιος': 'sfânt', 'ἁγίῳ': 'sfânt', 'ἅγιον': 'sfânt',
    'μέγας': 'mare', 'μεγάλη': 'mare', 'μεγάλῃ': 'mare',
    'νεκρός': 'mort', 'νεκρῶν': 'morților',
    'ἀληθινός': 'adevărat', 'ἀληθής': 'adevărat',
    'τυφλός': 'orb',
}

# Hebrew VT → Romanian (common words)
HEBREW_RO = {
    # Dumnezeu, nume
    'יהוה': 'YHWH', 'אלהים': 'Dumnezeu', 'אדני': 'Domnul',
    'אל': 'Dumnezeu',
    'ישוע': 'Iisus/Iosua', 'משיח': 'Mesia', 'דוד': 'David',
    'אברהם': 'Avraam', 'משה': 'Moise', 'אליהו': 'Ilie',
    'ישראל': 'Israel', 'אלעזר': 'Elazar/Lazăr',
    'שת': 'Set',
    # Locuri
    'ציון': 'Sion', 'ירושלם': 'Ierusalim',
    'היכל': 'Templu', 'מקדש': 'sanctuar',
    'בבל': 'Babilon', 'מצרים': 'Egipt',
    # Concepte
    'תורה': 'Tora/Legea', 'ברית': 'legământ',
    'שבת': 'Sabat', 'פסח': 'Paște',
    'קרבן': 'jertfă', 'כהן': 'preot', 'נביא': 'profet',
    'מלאך': 'înger', 'עבד': 'rob/slujitor',
    # Atribute
    'אמת': 'adevăr', 'חסד': 'har/milă',
    'שלום': 'pace', 'צדק': 'dreptate',
    'כבוד': 'slavă', 'קדש': 'sfânt',
    'אור': 'lumină', 'חשך': 'întuneric',
    # Viață, moarte
    'חיים': 'viață', 'חי': 'viu', 'מות': 'moarte', 'מת': 'mort',
    'נפש': 'suflet', 'רוח': 'duh/spirit', 'בשר': 'trup',
    'דם': 'sânge', 'מים': 'apă', 'לחם': 'pâine', 'יין': 'vin',
    'דבר': 'cuvânt', 'לשון': 'limbă',
    # Natură, obiecte
    'שמים': 'ceruri', 'ארץ': 'pământ',
    'אבן': 'piatră', 'עץ': 'copac/lemn',
    'גפן': 'viță', 'שרק': 'viță aleasă',
    'בגד': 'haină', 'עיר': 'mânz',
    'יונה': 'porumbel', 'שה': 'miel',
    'מערה': 'peșteră', 'קבר': 'mormânt',
    'שכינה': 'Shekinah/prezență',
    'תכריכים': 'giulgiuri',
    'עניה': 'suferință',
    # Acțiuni (rădăcini)
    'גאלה': 'răscumpărare', 'משפט': 'judecată',
    'אות': 'semn', 'מופת': 'minune',
    'בן': 'fiu', 'אדם': 'om',
    # Cifru
    'ששך': 'Sheshak (=Babilon)',
}


def greek_to_ro(word: str, lemma: str = '') -> str:
    """Translate a Greek word to Romanian (or English via Strong's).

    Tries: exact form in Romanian dict → lemma in Romanian dict → lemma in Strong's.
    """
    # 1. Manual Romanian JSON (lexicon_ro.json — 200 lemme, precise)
    if lemma and lemma in _LEXICON_RO:
        return _LEXICON_RO[lemma]
    if word in _LEXICON_RO:
        return _LEXICON_RO[word]
    # 2. Inline Romanian dict (GREEK_RO — forms + lemmas)
    if word in GREEK_RO:
        return GREEK_RO[word]
    if lemma and lemma in GREEK_RO:
        return GREEK_RO[lemma]
    # 3. Strong's Romanian (strongs_ro.json — auto-translated, less precise)
    if lemma and lemma in _STRONGS_RO:
        return _STRONGS_RO[lemma]
    if word in _STRONGS_RO:
        return _STRONGS_RO[word]
    # 4. Strong's English (strongs_greek.json — last resort)
    if lemma and lemma in _STRONGS_EN:
        return _STRONGS_EN[lemma]
    if word in _STRONGS_EN:
        return _STRONGS_EN[word]
    return ''


def hebrew_to_ro(word: str) -> str:
    """Translate a Hebrew word to Romanian. Returns '' if not found."""
    return HEBREW_RO.get(word, '')
