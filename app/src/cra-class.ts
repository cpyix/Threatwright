// CRA classification for orientation in the setup wizard: Regulation (EU) 2024/2847, Art. 2, 7, 8, 32,
// Annex III and IV (OJ L, 20.11.2024). Own short wording; nothing here is stored or reported.
import type { I18n } from './types'

export const SCOPE_EXCLUSIONS: I18n[] = [
  {
    de: 'Medizinprodukte und In-vitro-Diagnostika nach MDR (EU) 2017/745 bzw. IVDR (EU) 2017/746 (Art. 2 Abs. 2)',
    en: 'Medical devices and in vitro diagnostics under MDR (EU) 2017/745 or IVDR (EU) 2017/746 (Art. 2(2))',
  },
  {
    de: 'Fahrzeuge, Systeme und Bauteile mit Typgenehmigung nach Verordnung (EU) 2019/2144 (Art. 2 Abs. 2)',
    en: 'Vehicles, systems and components with type approval under Regulation (EU) 2019/2144 (Art. 2(2))',
  },
  {
    de: 'Zivilluftfahrt: nach Verordnung (EU) 2018/1139 zertifizierte Produkte (Art. 2 Abs. 3)',
    en: 'Civil aviation: products certified under Regulation (EU) 2018/1139 (Art. 2(3))',
  },
  {
    de: 'Schiffsausrüstung nach Richtlinie 2014/90/EU (Art. 2 Abs. 4)',
    en: 'Marine equipment under Directive 2014/90/EU (Art. 2(4))',
  },
  {
    de: 'Ersatzteile, die baugleiche Komponenten ersetzen (Art. 2 Abs. 6)',
    en: 'Spare parts replacing identical components (Art. 2(6))',
  },
  {
    de: 'Produkte ausschließlich für nationale Sicherheit oder Verteidigung (Art. 2 Abs. 7)',
    en: 'Products made exclusively for national security or defence (Art. 2(7))',
  },
  {
    de: 'Freie und Open-Source-Software, die nicht im Rahmen einer Geschäftstätigkeit bereitgestellt wird (Erwägungsgrund 18)',
    en: 'Free and open-source software not supplied in the course of a commercial activity (recital 18)',
  },
  {
    de: 'Reine Cloud-Dienste (SaaS) ohne zugehöriges Produkt; die Fernverarbeitung, die Ihr Produkt für eine Funktion braucht, gehört dagegen dazu (Erwägungsgrund 12)',
    en: 'Pure cloud services (SaaS) without a product; remote data processing your product needs for one of its functions is covered (recital 12)',
  },
]

type Cls = 'I' | 'II' | 'critical'
const c = (id: string, cls: Cls, de: string, en: string, examples?: I18n) => ({ id, cls, label: { de, en }, examples })

export const CATEGORIES_CRA: { id: string; cls: Cls; label: I18n; examples?: I18n }[] = [
  // Annex III, class I
  c('III-I-1', 'I', 'Identitäts- und privilegierte Zugriffsverwaltung', 'Identity and privileged access management', {
    de: 'auch Authentifizierungs- und Zutrittsleser, z. B. biometrisch',
    en: 'including authentication and access control readers, e.g. biometric',
  }),
  c('III-I-2', 'I', 'Browser, eigenständig oder eingebettet', 'Browsers, standalone or embedded'),
  c('III-I-3', 'I', 'Passwortmanager', 'Password managers'),
  c('III-I-4', 'I', 'Software, die Schadprogramme sucht, entfernt oder isoliert', 'Software that finds, removes or quarantines malware'),
  c('III-I-5', 'I', 'Produkte mit VPN-Funktion', 'Products with a VPN function'),
  c('III-I-6', 'I', 'Netzwerkmanagementsysteme', 'Network management systems'),
  c('III-I-7', 'I', 'SIEM-Systeme (Sicherheitsereignisse sammeln und auswerten)', 'SIEM systems (collect and analyse security events)'),
  c('III-I-8', 'I', 'Bootmanager', 'Boot managers'),
  c('III-I-9', 'I', 'PKI und Software zur Ausstellung digitaler Zertifikate', 'PKI and software issuing digital certificates'),
  c('III-I-10', 'I', 'Physische und virtuelle Netzwerkschnittstellen', 'Physical and virtual network interfaces'),
  c('III-I-11', 'I', 'Betriebssysteme', 'Operating systems'),
  c('III-I-12', 'I', 'Router, Modems für den Internetanschluss und Switches', 'Routers, modems for internet access and switches'),
  c('III-I-13', 'I', 'Mikroprozessoren mit Sicherheitsfunktionen', 'Microprocessors with security functions'),
  c('III-I-14', 'I', 'Mikrocontroller mit Sicherheitsfunktionen', 'Microcontrollers with security functions'),
  c('III-I-15', 'I', 'ASICs und FPGAs mit Sicherheitsfunktionen', 'ASICs and FPGAs with security functions'),
  c('III-I-16', 'I', 'Allgemeine virtuelle Assistenten für das Smart Home', 'General-purpose smart home virtual assistants'),
  c('III-I-17', 'I', 'Smart-Home-Produkte mit Sicherheitsfunktionen', 'Smart home products with security functions', {
    de: 'z. B. smarte Türschlösser, Sicherheitskameras, Babyphones, Alarmanlagen',
    en: 'e.g. smart door locks, security cameras, baby monitors, alarm systems',
  }),
  c('III-I-18', 'I', 'Vernetztes Spielzeug mit sozialer Interaktion oder Ortung', 'Internet-connected toys with social interaction or location tracking', {
    de: 'Spielzeug nach Richtlinie 2009/48/EG, das z. B. spricht, filmt oder den Standort erfasst',
    en: 'toys under Directive 2009/48/EC that e.g. speak, film or track location',
  }),
  c('III-I-19', 'I', 'Am Körper getragene Produkte zur Gesundheitsüberwachung oder für Kinder', 'Wearables for health monitoring or for children', {
    de: 'Gesundheitsüberwachung nur, soweit nicht MDR oder IVDR gelten',
    en: 'health monitoring only where MDR or IVDR do not apply',
  }),
  // Annex III, class II
  c('III-II-1', 'II', 'Hypervisoren und Container-Laufzeitumgebungen', 'Hypervisors and container runtime systems'),
  c('III-II-2', 'II', 'Firewalls, Systeme zur Erkennung und Abwehr von Angriffen (IDS/IPS)', 'Firewalls, intrusion detection and prevention systems (IDS/IPS)'),
  c('III-II-3', 'II', 'Manipulationssichere Mikroprozessoren', 'Tamper-resistant microprocessors'),
  c('III-II-4', 'II', 'Manipulationssichere Mikrocontroller', 'Tamper-resistant microcontrollers'),
  // Annex IV
  c('IV-1', 'critical', 'Hardwaregeräte mit Sicherheitsboxen', 'Hardware devices with security boxes'),
  c('IV-2', 'critical', 'Smart-Meter-Gateways und andere Geräte für erweiterte Sicherheitszwecke', 'Smart meter gateways and other devices for advanced security purposes', {
    de: 'z. B. für sichere Kryptoverarbeitung',
    en: 'e.g. for secure cryptoprocessing',
  }),
  c('IV-3', 'critical', 'Smartcards und ähnliche Geräte, auch Secure Elements', 'Smartcards and similar devices, including secure elements'),
]

export const PROCEDURE: Record<'default' | Cls, I18n> = {
  default: {
    de: 'Sie können die Konformität selbst bewerten (interne Kontrolle, Modul A, Art. 32 Abs. 1); eine benannte Stelle ist nicht vorgeschrieben.',
    en: 'You may assess conformity yourself (internal control, module A, Art. 32(1)); a notified body is not required.',
  },
  I: {
    de:
      'Modul A genügt nur, wenn Sie harmonisierte Normen, gemeinsame Spezifikationen oder eine europäische Cybersicherheitszertifizierung ' +
      '(mindestens Stufe „substanziell“, z. B. EUCC) vollständig anwenden; sonst EU-Baumusterprüfung (Modul B + C) oder ' +
      'umfassende Qualitätssicherung (Modul H) mit einer benannten Stelle (Art. 32 Abs. 2).',
    en:
      'Module A is enough only if you fully apply harmonised standards, common specifications or a European cybersecurity ' +
      'certification scheme (at least “substantial”, e.g. EUCC); otherwise EU-type examination (module B + C) or full quality ' +
      'assurance (module H) with a notified body (Art. 32(2)).',
  },
  II: {
    de:
      'EU-Baumusterprüfung (Modul B + C) oder umfassende Qualitätssicherung (Modul H) mit einer benannten Stelle, oder, wo verfügbar, ' +
      'eine europäische Cybersicherheitszertifizierung mindestens der Stufe „substanziell“, z. B. EUCC (Art. 32 Abs. 3); Modul A allein genügt nicht.',
    en:
      'EU-type examination (module B + C) or full quality assurance (module H) with a notified body, or, where available, a European ' +
      'cybersecurity certification scheme at level “substantial” or higher, e.g. EUCC (Art. 32(3)); module A alone is not enough.',
  },
  critical: {
    de:
      'Europäisches Cybersicherheitszertifikat, sobald ein delegierter Rechtsakt nach Art. 8 Abs. 1 es für Ihre Kategorie verlangt; ' +
      'bis dahin wie Klasse II (Art. 32 Abs. 4).',
    en:
      'A European cybersecurity certificate once a delegated act under Art. 8(1) requires it for your category; until then as ' +
      'class II (Art. 32(4)).',
  },
}

export const CLASS_NAME: Record<'default' | Cls, I18n> = {
  default: { de: 'Standard: keine wichtige oder kritische Produktkategorie', en: 'Default: no important or critical product category' },
  I: { de: 'Wichtiges Produkt, Klasse I (Anhang III)', en: 'Important product, Class I (Annex III)' },
  II: { de: 'Wichtiges Produkt, Klasse II (Anhang III)', en: 'Important product, Class II (Annex III)' },
  critical: { de: 'Kritisches Produkt (Anhang IV)', en: 'Critical product (Annex IV)' },
}

export const CRA_TEXT = {
  de: {
    notice:
      'Nur zur Orientierung, keine rechtliche Bewertung. Hier wird nichts gespeichert, und nichts davon erscheint im Dokument. ' +
      'Prüfen Sie die Einstufung anhand der Verordnung (EU) 2024/2847 (Art. 7, Anhang III und IV) und des Durchführungsrechtsakts ' +
      'nach Art. 7 Abs. 4, der die Kategorien technisch beschreibt.',
    skip: 'Sie können diesen Schritt mit „Weiter“ überspringen.',
    scope_q: 'Fällt Ihr Produkt unter den CRA?',
    scope_text:
      'Der CRA gilt für Produkte mit digitalen Elementen, die direkt oder indirekt mit einem Gerät oder Netz Daten austauschen können ' +
      'und in der EU im Rahmen einer Geschäftstätigkeit bereitgestellt werden (Art. 2 Abs. 1). Ausgenommen sind unter anderem:',
    yes: 'Ja',
    no: 'Nein, eine Ausnahme trifft zu',
    unsure: 'Unsicher',
    category_q: 'Gehört die Kernfunktion zu einer dieser Kategorien?',
    category_hint:
      'Maßgeblich ist die Kernfunktion (Art. 7 Abs. 1). Ein vernetztes Gerät, etwa ein Thermostat, gehört nur dann zu Anhang III, ' +
      'wenn seine Kernfunktion eine dieser Kategorien ist. Eine eingebaute Komponente, z. B. ein Betriebssystem, macht das Produkt ' +
      'nicht selbst zu einem wichtigen Produkt.',
    class_I: 'Anhang III, Klasse I',
    class_II: 'Anhang III, Klasse II',
    class_critical: 'Anhang IV, kritische Produkte',
    none: 'keine davon',
    result: 'Ergebnis',
    pick: 'Wählen Sie oben eine Kategorie oder „keine davon“.',
    out_of_scope:
      'Nach Ihrer Angabe fällt das Produkt nicht unter den CRA. Prüfen Sie die Ausnahme anhand des genannten Rechtsakts.',
    same:
      'Die Risikobeurteilung in Threatwright ist in jedem Fall dieselbe; die Einstufung bestimmt nur das Konformitätsbewertungsverfahren.',
  },
  en: {
    notice:
      'For orientation only, not a legal assessment. Nothing here is stored, and none of it appears in the document. ' +
      'Check the classification against Regulation (EU) 2024/2847 (Art. 7, Annex III and IV) and the implementing act under ' +
      'Art. 7(4), which gives the technical description of the categories.',
    skip: 'You can skip this step with “Next”.',
    scope_q: 'Does your product fall under the CRA?',
    scope_text:
      'The CRA applies to products with digital elements that can exchange data directly or indirectly with a device or network ' +
      'and are supplied on the EU market in the course of a commercial activity (Art. 2(1)). Excluded are, among others:',
    yes: 'Yes',
    no: 'No, an exclusion applies',
    unsure: 'Not sure',
    category_q: 'Is the core function one of these categories?',
    category_hint:
      'What counts is the core function (Art. 7(1)). A connected device such as a thermostat only falls under Annex III if its ' +
      'core function is one of these categories. A built-in component, e.g. an operating system, does not by itself make the ' +
      'product an important product.',
    class_I: 'Annex III, class I',
    class_II: 'Annex III, class II',
    class_critical: 'Annex IV, critical products',
    none: 'none of these',
    result: 'Result',
    pick: 'Choose a category above or “none of these”.',
    out_of_scope: 'According to your answer the product does not fall under the CRA. Check the exclusion against the legal act named.',
    same: 'The risk assessment in Threatwright is the same in every case; the classification only determines the conformity assessment procedure.',
  },
}
