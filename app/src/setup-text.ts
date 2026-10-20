// Texts of the setup wizard (own wording; references to CRA and TR-03183-1 are by section only).
import type { Lang } from './types'

const de = {
  title: 'Einrichtungsassistent',
  step: 'Schritt',
  of: 'von',
  next: 'Weiter',
  back: 'Zurück',
  skip: 'Assistent beenden',
  start: 'Los geht’s',

  intro_title: 'Ihr erstes Bedrohungsmodell in sieben Schritten',
  intro_text:
    'Der Assistent führt Sie von der Produktbeschreibung bis zu den ersten Bedrohungen nach BSI TR-03183-1. ' +
    'Alles, was Sie hier anlegen, ist normaler Modellinhalt und lässt sich später in jeder Ansicht ändern. ' +
    'Sie können den Assistenten jederzeit verlassen und über „Einrichtung“ in der Navigation fortsetzen.',
  intro_save: 'Auf die Festplatte geschrieben wird erst mit „Speichern“ (Strg+S). Rückgängig (Strg+Z) funktioniert in jedem Schritt.',
  intro_time: 'Planen Sie für ein überschaubares Produkt etwa 30 bis 60 Minuten ein.',

  s_product: 'Produkt und Einsatzzweck',
  s_zones: 'Einsatzumgebung und Zonen',
  s_elements: 'Komponenten',
  s_flows: 'Verbindungen',
  s_assets: 'Assets',
  s_threats: 'Bedrohungen',
  s_finish: 'Abschluss',

  product_text:
    'Beschreiben Sie, was betrachtet wird. Der CRA verlangt, die Risikobewertung auf Zweckbestimmung, ' +
    'vernünftigerweise vorhersehbare Verwendung und Einsatzbedingungen zu stützen (Art. 13 Abs. 3). ' +
    'Diese Beschreibung erscheint im erzeugten Dokument.',
  product_questions: 'Leitfragen',
  product_q: [
    'Wofür wird das Produkt eingesetzt, und welche Fehlanwendung ist vorhersehbar?',
    'Wer arbeitet damit: Bediener, Instandhaltung, Service des Herstellers, Fernwartung?',
    'Wo steht es: Schaltschrank, Produktionshalle, frei zugänglich, Außenbereich?',
    'Welche Schnittstellen hat es: Netzwerk, Feldbus, USB, Funk, Cloud?',
    'Was gehört nicht dazu (Systemgrenze), z. B. das Netz des Betreibers?',
  ],
  model_title: 'Titel des Modells',
  description: 'Beschreibung (Zweck, Verwendung, Umgebung, Systemgrenze)',
  description_placeholder:
    'Zweck: …\nVorhersehbare Verwendung und Fehlanwendung: …\nEinsatzumgebung: …\nNutzergruppen: …\nSystemgrenze: …',
  configurations: 'Ausbaustufen / Varianten',
  configurations_help:
    'Gibt es das Produkt in Varianten mit unterschiedlichen Schnittstellen (z. B. mit oder ohne Fernwartung)? ' +
    'Legen Sie je Ausbaustufe / Variante einen Eintrag an. Elemente und Bedrohungen lassen sich später darauf einschränken. ' +
    'Ohne Varianten genügt „Standard“.',
  add_configuration: '+ Ausbaustufe / Variante',

  zones_text:
    'Zonen fassen Komponenten mit gleicher Erreichbarkeit zusammen; jede Grenze zwischen Zonen ist eine Vertrauensgrenze. ' +
    'Je Zone legen Sie fest, über welche Schnittstelle ein Angreifer hinkommt, wer physisch Zugang hat und wer das Gerät bedient. ' +
    'Daraus berechnet die Methode die Exposition (TR-03183-1 Anhang D); neue Bedrohungen übernehmen diese Werte als Vorbelegung.',
  zones_hint: 'Die vier vorgeschlagenen Zonen passen für die meisten Maschinen. Benennen Sie sie um oder ergänzen Sie eigene.',
  add_zone: '+ Zone',
  zone_title: 'Bezeichnung',
  not_set: '– bitte wählen –',

  elements_text:
    'Wählen Sie die Bausteine Ihres Produkts aus der OT-Bibliothek. Jeder Baustein bringt seine typischen Assets mit und ' +
    'liefert später passende Bedrohungsvorschläge. Externe Einheiten wie Servicelaptop oder USB-Stick gehören dazu, ' +
    'wenn sie mit dem Produkt kommunizieren.',
  elements_hint: 'Gleiche Bausteine mehrfach anlegen, wenn sie unterschiedlich angebunden sind (z. B. zwei Antriebe an verschiedenen Bussen).',
  library: 'Bibliothek',
  added: 'Im Modell',
  element_name: 'Bezeichnung',
  zone: 'Zone',
  add: 'Anlegen',
  brings_assets: 'bringt mit',
  none_yet: 'Noch nichts angelegt.',
  preview: 'So sieht Ihr Modell aus',
  preview_help:
    'Das ist das Diagramm. Ziehen Sie Elemente in eine andere Zone oder ziehen Sie eine Verbindung von einem Anfasser zum nächsten Element.',
  remove: 'Entfernen',
  search: 'Suchen …',

  flows_text:
    'Verbinden Sie Komponenten, die Daten austauschen. Verbindungen über Zonengrenzen sind typische Angriffswege. ' +
    'Wählen Sie, wenn möglich, den Typ (z. B. EtherCAT, IP-Netz, VPN), damit passende Bedrohungen vorgeschlagen werden.',
  flows_hint: 'Typisch: Bedienpanel ↔ Steuerung, Steuerung ↔ Antriebe/I/O (Feldbus), Steuerung ↔ Anlagennetz, Fernwartung ↔ Router.',
  source: 'Von',
  target: 'Nach',
  flow_type: 'Typ',
  generic_flow: 'allgemeine Verbindung',
  connect: 'Verbinden',
  crosses: 'über Zonengrenze',
  need_two: 'Legen Sie zuerst mindestens zwei Komponenten an.',

  assets_text:
    'Assets sind die Werte, die geschützt werden müssen: Funktionen, Daten, Parameter, Schlüssel. ' +
    'Die TR-Klasse bestimmt die Grundauswirkung bei Verlust von Vertraulichkeit (C), Integrität (I) und Verfügbarkeit (A), ' +
    'Stufe 1 (sehr gering) bis 5 (sehr hoch). Die Komponenten haben typische Assets angelegt: ' +
    'prüfen Sie die Klasse, löschen Sie, was nicht zutrifft, und ergänzen Sie, was fehlt, etwa Rezepturen oder Kundendaten.',
  asset_title: 'Asset',
  asset_class: 'TR-Klasse',
  impact: 'Impact C / I / A',
  protects: 'schützt',
  protects_help: 'Sicherheits-Assets erben ihren Schutzbedarf von den Assets, die sie schützen. Bitte auswählen.',
  add_asset: 'Asset hinzufügen',

  threats_text:
    'Für jede Komponente und Verbindung schlägt die Bibliothek Bedrohungen nach STRIDE vor. ' +
    'Übernehmen Sie, was für Ihr Produkt zutrifft; die vorgeschlagenen Maßnahmen kommen automatisch mit. ' +
    'Unpassendes lassen Sie weg, die Abdeckungsmatrix erinnert später an Lücken.',
  threats_cyber:
    'Zu jeder übernommenen Bedrohung fragt die TR, ob die Ursache ein Angriff auf das digitale Produkt ist (Regel 3.3). ' +
    'Nur dann ist es ein Cyberrisiko; sonst wird die Bedrohung mit Begründung verworfen.',
  adopt_selected: 'Ausgewählte übernehmen',
  adopted: 'übernommen',
  adopted_of: 'übernommen',
  more: 'Weitere Vorschläge',
  no_suggestions: 'Keine Vorschläge für diesen Baustein.',
  flow_needs_type:
    'Für eine allgemeine Verbindung gibt es keine Vorlagen. Wählen Sie im Schritt „Verbindungen“ den Typ (z. B. EtherCAT, IP-Netz), dann erscheinen passende Vorschläge.',
  open_cyber: 'Offene Frage: Ist die Ursache ein Angriff auf das digitale Produkt?',
  open_cyber_help: 'Lesen Sie das Szenario und entscheiden Sie einzeln. Bei „Nein“ wird die Bedrohung mit Begründung verworfen.',
  yes: 'Ja, Cyberrisiko',
  no: 'Nein …',
  loading: 'Lädt …',

  finish_text:
    'Das Grundgerüst steht. Ab hier arbeiten Sie in den normalen Ansichten weiter. So geht es weiter:',
  checklist: 'Stand',
  c_description: 'Produktbeschreibung vorhanden',
  c_zones: 'Alle Zonen vollständig bewertet',
  c_elements: 'Komponenten angelegt',
  c_flows: 'Verbindungen angelegt',
  c_assets: 'Assets klassifiziert',
  c_threats: 'Bedrohungen übernommen',
  c_cyber: 'Ursachenfrage beantwortet',
  c_errors: 'Fehler in der Prüfung',
  show_errors: 'Fehler ansehen →',
  next_steps: 'Nächste Schritte',
  n_assess: 'Bedrohungen bewerten: Schnittstelle, Zugang und Nutzer prüfen, Impact setzen und begründen.',
  n_coverage: 'Abdeckung prüfen: Lücken schließen oder als „nicht relevant“ begründen.',
  n_measures: 'Maßnahmen beschließen und Restrisiko eintragen.',
  n_validate: 'Prüfung ohne Fehler abschließen.',
  n_save: 'Speichern, in Git committen und das Dokument erzeugen.',
  go_threats: 'Zu den Bedrohungen',
  go_coverage: 'Zur Abdeckung',
  go_diagram: 'Zum Diagramm',
  save_now: 'Jetzt speichern',
  no_model: 'Das Projekt hat noch kein Teilmodell. Der Assistent legt das Teilmodell „main“ an.',
  create_model: 'Teilmodell anlegen',
}

type Text = { [K in keyof typeof de]: (typeof de)[K] extends string[] ? string[] : string }

const en: Text = {
  title: 'Setup wizard',
  step: 'Step',
  of: 'of',
  next: 'Next',
  back: 'Back',
  skip: 'Close wizard',
  start: 'Let’s start',

  intro_title: 'Your first threat model in seven steps',
  intro_text:
    'The wizard takes you from the product description to the first threats according to BSI TR-03183-1. ' +
    'Everything you create here is regular model content and can be changed later in every view. ' +
    'You can leave the wizard at any time and continue via “Setup” in the navigation.',
  intro_save: 'Nothing is written to disk until you save (Ctrl+S). Undo (Ctrl+Z) works in every step.',
  intro_time: 'Plan about 30 to 60 minutes for a manageable product.',

  s_product: 'Product and intended purpose',
  s_zones: 'Operating environment and zones',
  s_elements: 'Components',
  s_flows: 'Connections',
  s_assets: 'Assets',
  s_threats: 'Threats',
  s_finish: 'Finish',

  product_text:
    'Describe what is analysed. The CRA requires the risk assessment to be based on the intended purpose, ' +
    'reasonably foreseeable use and the conditions of use (Art. 13(3)). This description appears in the generated document.',
  product_questions: 'Guiding questions',
  product_q: [
    'What is the product used for, and which misuse is foreseeable?',
    'Who works with it: operators, maintenance, manufacturer service, remote maintenance?',
    'Where is it installed: control cabinet, production hall, publicly accessible, outdoors?',
    'Which interfaces does it have: network, fieldbus, USB, wireless, cloud?',
    'What is out of scope (system boundary), e.g. the operator’s network?',
  ],
  model_title: 'Model title',
  description: 'Description (purpose, use, environment, system boundary)',
  description_placeholder:
    'Purpose: …\nForeseeable use and misuse: …\nOperating environment: …\nUser groups: …\nSystem boundary: …',
  configurations: 'Variants and configuration levels',
  configurations_help:
    'Does the product come in variants with different interfaces (e.g. with or without remote maintenance)? ' +
    'Create one configuration level per variant; elements and threats can be restricted to it later. ' +
    'Without variants, “Standard” is enough.',
  add_configuration: '+ Configuration level',

  zones_text:
    'Zones group components with the same reachability; every border between zones is a trust boundary. ' +
    'For each zone, set the interface an attacker uses, who has physical access and who operates the device. ' +
    'The method derives the exposure from this (TR-03183-1 Annex D); new threats take these values as defaults.',
  zones_hint: 'The four suggested zones fit most machines. Rename them or add your own.',
  add_zone: '+ Zone',
  zone_title: 'Name',
  not_set: '– please choose –',

  elements_text:
    'Choose the building blocks of your product from the OT library. Each brings its typical assets and later ' +
    'offers fitting threat suggestions. External entities such as a service laptop or USB stick belong here ' +
    'if they communicate with the product.',
  elements_hint: 'Add the same building block several times if the instances are connected differently (e.g. two drives on different buses).',
  library: 'Library',
  added: 'In the model',
  element_name: 'Name',
  zone: 'Zone',
  add: 'Add',
  brings_assets: 'brings',
  none_yet: 'Nothing added yet.',
  preview: 'Your model so far',
  preview_help: 'This is the diagram. Drag elements into another zone or drag a connection from a handle to another element.',
  remove: 'Remove',
  search: 'Search …',

  flows_text:
    'Connect components that exchange data. Connections across zone borders are typical attack paths. ' +
    'Choose the type where possible (e.g. EtherCAT, IP network, VPN) so that fitting threats are suggested.',
  flows_hint: 'Typical: HMI ↔ controller, controller ↔ drives/I/O (fieldbus), controller ↔ plant network, remote maintenance ↔ router.',
  source: 'From',
  target: 'To',
  flow_type: 'Type',
  generic_flow: 'generic connection',
  connect: 'Connect',
  crosses: 'crosses zone border',
  need_two: 'Add at least two components first.',

  assets_text:
    'Assets are the values to protect: functions, data, parameters, keys. The TR class sets the base impact of a loss of ' +
    'confidentiality (C), integrity (I) and availability (A), level 1 (very low) to 5 (very high). The components have ' +
    'created typical assets: check the class, delete what does not apply and add what is missing, e.g. recipes or customer data.',
  asset_title: 'Asset',
  asset_class: 'TR class',
  impact: 'Impact C / I / A',
  protects: 'protects',
  protects_help: 'Security assets inherit their protection needs from the assets they protect. Please select them.',
  add_asset: 'Add asset',

  threats_text:
    'For every component and connection the library suggests threats by STRIDE category. Adopt what applies to your ' +
    'product; the suggested measures are added automatically. Leave out what does not fit; the coverage matrix will ' +
    'remind you of gaps later.',
  threats_cyber:
    'For every adopted threat the TR asks whether the cause is an attack on the digital product (rule 3.3). ' +
    'Only then is it a cyber risk; otherwise the threat is rejected with a rationale.',
  adopt_selected: 'Adopt selected',
  adopted: 'adopted',
  adopted_of: 'adopted',
  more: 'More suggestions',
  no_suggestions: 'No suggestions for this building block.',
  flow_needs_type:
    'A generic connection has no templates. Choose its type (e.g. EtherCAT, IP network) in the "Connections" step to get matching suggestions.',
  open_cyber: 'Open question: is the cause an attack on the digital product?',
  open_cyber_help: 'Read the scenario and decide for each one. "No" rejects the threat with a rationale.',
  yes: 'Yes, cyber risk',
  no: 'No …',
  loading: 'Loading …',

  finish_text: 'The basic structure is in place. From here, continue in the regular views:',
  checklist: 'Status',
  c_description: 'Product description present',
  c_zones: 'All zones fully rated',
  c_elements: 'Components added',
  c_flows: 'Connections added',
  c_assets: 'Assets classified',
  c_threats: 'Threats adopted',
  c_cyber: 'Cause question answered',
  c_errors: 'Errors in the validation',
  show_errors: 'Show errors →',
  next_steps: 'Next steps',
  n_assess: 'Assess threats: check interface, access and user, set and justify the impact.',
  n_coverage: 'Check coverage: close gaps or justify them as “not relevant”.',
  n_measures: 'Decide on measures and enter the residual risk.',
  n_validate: 'Finish the validation without errors.',
  n_save: 'Save, commit to Git and generate the document.',
  go_threats: 'Go to threats',
  go_coverage: 'Go to coverage',
  go_diagram: 'Go to diagram',
  save_now: 'Save now',
  no_model: 'The project has no model yet. The wizard creates the model “main”.',
  create_model: 'Create model',
}

export const CATEGORIES: Record<Lang, Record<string, string>> = {
  de: {
    controllers: 'Steuerungen',
    operation: 'Bedienung und Engineering',
    field: 'Antriebe und Feldebene',
    network: 'Netzwerk und Kommunikation',
    remote: 'Fernzugriff und Dienste',
    data: 'Datenspeicher',
    safety: 'Sicherheitsschnittstelle (Safety)',
    media: 'Wechseldatenträger',
    other: 'Weitere',
  },
  en: {
    controllers: 'Controllers',
    operation: 'Operation and engineering',
    field: 'Drives and field level',
    network: 'Network and communication',
    remote: 'Remote access and services',
    data: 'Data stores',
    safety: 'Safety interface',
    media: 'Removable media',
    other: 'Other',
  },
}

// Short own-words explanation of the TR-03183-1 asset classes (Tables 1-3).
/** Readable option text for an asset class: the description without its example. */
export const assetClassLabel = (lang: Lang, cls: string): string =>
  ASSET_CLASSES[lang][cls]?.split(' (')[0] ?? cls

export const ASSET_CLASSES: Record<Lang, Record<string, string>> = {
  de: {
    'PII.TechnicalNecessary': 'Personenbezogene Daten, die nur technisch nötig sind (z. B. Benutzerkennung im Protokoll)',
    'PII.Generic': 'Allgemeine personenbezogene Daten (z. B. Name, Schichtzuordnung)',
    'PII.Important': 'Besonders schutzwürdige personenbezogene Daten (z. B. biometrische Daten)',
    'BusinessData.Generic': 'Allgemeine Betriebs- und Produktionsdaten',
    'BusinessData.Important': 'Wichtige Geschäftsdaten und Know-how (z. B. Steuerungsprogramm, Rezepturen)',
    'Other.Telemetric': 'Telemetrie- und Diagnosedaten ohne besonderen Wert',
    'Other.Configuration': 'Konfiguration und Parameter, deren Änderung das Verhalten beeinflusst',
    'Functions.Essential': 'Wesentliche Funktion; ihr Ausfall stoppt den Betrieb',
    'Functions.NonEssential': 'Nebenfunktion (Komfort, Anzeige); Ausfall verkraftbar',
    'Functions.Safety': 'Funktion mit Schutzwirkung für Personen (Safety)',
    'Functions.CommunicationNetwork': 'Kommunikation über Netzwerke',
    'Functions.CommunicationLocal': 'Lokale Kommunikation (z. B. Feldbus im Schaltschrank, USB)',
    'Security.Secrets': 'Geheimnisse: Passwörter, Schlüssel, Zertifikate',
    'Security.PublicConfiguration': 'Öffentliche Sicherheitskonfiguration (z. B. öffentliche Schlüssel, Firewall-Regeln)',
    'Security.Logs': 'Sicherheitsprotokolle',
    'Security.Mechanism': 'Sicherheitsmechanismus (z. B. Anmeldung, Update-Prüfung)',
  },
  en: {
    'PII.TechnicalNecessary': 'Personal data needed only for technical reasons (e.g. user ID in a log)',
    'PII.Generic': 'General personal data (e.g. name, shift assignment)',
    'PII.Important': 'Sensitive personal data (e.g. biometric data)',
    'BusinessData.Generic': 'General operating and production data',
    'BusinessData.Important': 'Important business data and know-how (e.g. control program, recipes)',
    'Other.Telemetric': 'Telemetry and diagnostic data without particular value',
    'Other.Configuration': 'Configuration and parameters whose change affects the behaviour',
    'Functions.Essential': 'Essential function; its failure stops operation',
    'Functions.NonEssential': 'Secondary function (comfort, display); failure is tolerable',
    'Functions.Safety': 'Function protecting people (safety)',
    'Functions.CommunicationNetwork': 'Communication over networks',
    'Functions.CommunicationLocal': 'Local communication (e.g. fieldbus in the cabinet, USB)',
    'Security.Secrets': 'Secrets: passwords, keys, certificates',
    'Security.PublicConfiguration': 'Public security configuration (e.g. public keys, firewall rules)',
    'Security.Logs': 'Security logs',
    'Security.Mechanism': 'Security mechanism (e.g. login, update verification)',
  },
}

export const SETUP: Record<Lang, Text> = { de: de as Text, en }
