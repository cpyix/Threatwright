// Plain-language explanations behind the (i) buttons. Sources: docs/methodik.md,
// docs/faq-cyberrisiko.md, TR-03183-1 Annex D. Keep each entry short: what it is, why it matters, an example.
import type { Lang } from './types'

type Entry = Record<Lang, { title: string; text: string }>

export const GLOSSARY = {
  zone: {
    de: {
      title: 'Zone und Vertrauensgrenze',
      text: 'Eine Zone fasst Teile zusammen, die gleich gut geschützt und gleich erreichbar sind, z. B. „im Schaltschrank“ oder „im Firmennetz des Kunden“. Die Linie zwischen zwei Zonen ist eine Vertrauensgrenze: Wer sie überschreitet, kommt aus einer Umgebung mit anderem Schutz. Datenflüsse über eine Vertrauensgrenze sind die typischen Angriffswege und werden gestrichelt gezeichnet. Die Umgebung der Zone (Schnittstelle, Zugang, Nutzer) bestimmt die Exposition aller Elemente darin.',
    },
    en: {
      title: 'Zone and trust boundary',
      text: 'A zone groups parts that are equally protected and equally reachable, e.g. "inside the control cabinet" or "in the customer\'s plant network". The line between two zones is a trust boundary: whatever crosses it comes from an environment with different protection. Data flows across a trust boundary are the typical attack paths and are drawn dashed. The zone\'s environment (interface, access, user) sets the exposure of every element in it.',
    },
  },
  configurations: {
    de: {
      title: 'Ausbaustufen',
      text: 'Varianten desselben Produkts, die Sie getrennt verkaufen oder ausliefern, z. B. „Standard“ und „mit Fernwartung“. Ein Element oder Datenfluss, der nur in einer Variante vorkommt, ordnen Sie dieser Ausbaustufe zu. Ohne Zuordnung gilt es für alle. So sehen Sie im Diagramm und im Bericht, welche Bedrohungen nur eine Variante betreffen.',
    },
    en: {
      title: 'Configurations',
      text: 'Variants of the same product that you sell or ship separately, e.g. "standard" and "with remote service". Assign an element or data flow that only exists in one variant to that configuration; without an assignment it applies to all. The diagram and the report then show which threats only affect one variant.',
    },
  },
  kind: {
    de: {
      title: 'Art des Elements',
      text: 'Gerät: Hardware mit eigener Firmware (SPS, Antrieb, Router). Prozess: Software, die auf etwas läuft (Webserver, Engineering-Tool). Datenspeicher: Ort, an dem Daten liegen (Datenbank, Rezeptdatei, Log). Externe Entität: außerhalb Ihrer Verantwortung (Bediener, Kunden-IT, Cloud-Dienst eines Dritten).',
    },
    en: {
      title: 'Element kind',
      text: 'Device: hardware with its own firmware (PLC, drive, router). Process: software running on something (web server, engineering tool). Data store: where data rests (database, recipe file, log). External entity: outside your responsibility (operator, customer IT, a third-party cloud service).',
    },
  },
  flow: {
    de: {
      title: 'Datenfluss',
      text: 'Eine Verbindung, über die Daten oder Befehle zwischen zwei Elementen laufen, z. B. „HMI sendet Sollwerte an SPS über Profinet“. Ziehen Sie im Diagramm von einem Anfasser eines Elements zu einem anderen. Der Typ (z. B. EtherCAT, OPC UA) bringt passende Bedrohungsvorlagen mit; „allgemeiner Datenfluss“ hat nur allgemeine.',
    },
    en: {
      title: 'Data flow',
      text: 'A connection carrying data or commands between two elements, e.g. "HMI sends setpoints to the PLC via Profinet". In the diagram, drag from one element\'s handle to another. The type (e.g. EtherCAT, OPC UA) brings matching threat templates; "generic data flow" only brings general ones.',
    },
  },
  palette: {
    de: {
      title: 'Bausteine',
      text: 'Vorgefertigte Elementtypen aus der Bibliothek. Jeder Baustein bringt typische Assets und Bedrohungsvorlagen mit, die der STRIDE-Assistent später vorschlägt. Ziehen Sie ihn in die passende Zone, dann übernimmt er deren Umgebung.',
    },
    en: {
      title: 'Building blocks',
      text: 'Ready-made element types from the library. Each brings typical assets and threat templates that the STRIDE assistant suggests later. Drop it into the right zone and it takes over that zone\'s environment.',
    },
  },
  asset_class: {
    de: {
      title: 'Asset und Asset-Klasse',
      text: 'Ein Asset ist etwas Schützenswertes: eine Sicherheitsfunktion, Rezepturen, Zugangsdaten, die Verfügbarkeit der Anlage. Die Klasse nach TR-03183-1 (Tabellen 1–3) legt fest, wie schwer ein Schaden an Vertraulichkeit (C), Integrität (I) und Verfügbarkeit (A) wiegt. Daraus schlägt das Werkzeug den Impact einer Bedrohung vor.',
    },
    en: {
      title: 'Asset and asset class',
      text: 'An asset is something worth protecting: a safety function, recipes, credentials, plant availability. Its class after TR-03183-1 (tables 1–3) sets how severe damage to confidentiality (C), integrity (I) and availability (A) is. The tool derives the suggested impact of a threat from it.',
    },
  },
  protects: {
    de: {
      title: 'Schützt',
      text: 'Nur für Sicherheits-Assets wie Schlüssel oder Passwörter: Welche Assets hängen von ihnen ab? Ein Schlüssel ist so wertvoll wie das, was er schützt. Er erbt deshalb deren Impact.',
    },
    en: {
      title: 'Protects',
      text: 'Only for security assets such as keys or passwords: which assets depend on them? A key is as valuable as what it protects, so it inherits their impact.',
    },
  },
  stride: {
    de: {
      title: 'STRIDE',
      text: 'Sechs Fragen, um nichts zu übersehen. S – Spoofing: Kann sich jemand als dieses Element ausgeben? T – Tampering: Kann jemand Daten, Befehle oder Software verändern? R – Repudiation: Kann jemand eine Aktion abstreiten, weil sie nicht nachweisbar ist? I – Information disclosure: Können Daten abfließen? D – Denial of service: Kann jemand die Funktion stören oder lahmlegen? E – Elevation of privilege: Kann jemand mehr Rechte erlangen, als er haben darf?',
    },
    en: {
      title: 'STRIDE',
      text: 'Six questions so nothing is missed. S – Spoofing: can someone pretend to be this element? T – Tampering: can someone change data, commands or software? R – Repudiation: can someone deny an action because it is not traceable? I – Information disclosure: can data leak? D – Denial of service: can someone disrupt or stop the function? E – Elevation of privilege: can someone gain more rights than allowed?',
    },
  },
  cyber_cause: {
    de: {
      title: 'Cyber-Ursache (Regel 3.3)',
      text: 'Der CRA fragt nach Cybersicherheitsrisiken. Ein Eintrag zählt dazu, wenn seine Ursache ein Angriff auf das digitale Produkt ist: unbefugter Zugriff, Manipulation von Daten, Befehlen, Konfiguration oder Software, Abfluss von Daten oder Störung über digitale Wege. Ein Kabelbruch oder ein Bedienfehler ohne Angriff gehört in die funktionale Sicherheit. Die Folge bestimmt die Höhe des Risikos, nicht ob es ein Cyberrisiko ist. Beantworten Sie die Frage für jede Bedrohung einzeln.',
    },
    en: {
      title: 'Cyber cause (rule 3.3)',
      text: 'The CRA asks for cybersecurity risks. An entry counts if its cause is an attack on the digital product: unauthorised access, manipulation of data, commands, configuration or software, data leakage, or disruption by digital means. A broken cable or an operator error without an attack belongs to functional safety. The consequence sets how high the risk is, not whether it is a cyber risk. Answer the question for each threat on its own.',
    },
  },
  amplifier: {
    de: {
      title: 'Verstärker',
      text: 'Korrigiert den Impact eines Assets nach oben oder unten, wenn die Klasse aus der TR für Ihr Produkt nicht passt. Nur mit Begründung zulässig, denn Prüfer schauen genau hierauf.',
    },
    en: {
      title: 'Amplifier',
      text: 'Raises or lowers an asset\'s impact when the TR class does not fit your product. Only allowed with a rationale, because auditors look closely at it.',
    },
  },
  environment: {
    de: {
      title: 'Umgebung: Schnittstelle, Zugang, Nutzer',
      text: 'Wie leicht kommt ein Angreifer heran? Schnittstelle: von „physisch“ (nur mit Werkzeug am Gerät) bis „externes Netz“ (Internet). Zugang: von „beschränkt“ (abgeschlossener Schrank) bis „unbeschränkt“. Nutzer: von „nicht nutzerabhängig“ bis „Laie“. Daraus berechnet sich die Exposition 1–5. Die Werte kommen aus der Zone und lassen sich je Bedrohung anpassen.',
    },
    en: {
      title: 'Environment: interface, access, user',
      text: 'How easily can an attacker get at it? Interface: from "physical" (only with tools at the device) to "external network" (internet). Access: from "restricted" (locked cabinet) to "unrestricted". User: from "not user-related" to "layperson". Together they give the exposure 1–5. The values come from the zone and can be adjusted per threat.',
    },
  },
  impact: {
    de: {
      title: 'Impact',
      text: 'Wie schwer wiegt der Schaden, wenn der Angriff gelingt? 1 = kaum spürbar, 5 = z. B. Gefahr für Menschen oder Stillstand der Anlage. Das Werkzeug schlägt den höchsten Wert der betroffenen Assets vor; Sie entscheiden.',
    },
    en: {
      title: 'Impact',
      text: 'How severe is the damage if the attack succeeds? 1 = barely noticeable, 5 = e.g. danger to people or plant standstill. The tool suggests the highest value of the affected assets; you decide.',
    },
  },
  exposure: {
    de: {
      title: 'Exposition und Risiko',
      text: 'Die Exposition (1–5) sagt, wie erreichbar das Ziel ist. Sie wird aus der Umgebung berechnet. Exposition und Impact ergeben über die Matrix der TR das Risiko von 1 „sehr niedrig“ bis 5 „sehr hoch“. Bis „niedrig“ ist es akzeptabel, darüber brauchen Sie eine Maßnahme oder eine begründete Akzeptanz.',
    },
    en: {
      title: 'Exposure and risk',
      text: 'Exposure (1–5) says how reachable the target is; it is computed from the environment. Exposure and impact give the risk via the TR matrix, from 1 "very low" to 5 "very high". Up to "low" it is acceptable; above that you need a measure or a justified acceptance.',
    },
  },
  residual: {
    de: {
      title: 'Restrisiko',
      text: 'Das Risiko, das nach Umsetzung der Maßnahmen bleibt. Bewerten Sie Umgebung und Impact so, als wäre die Maßnahme schon wirksam, z. B. Zugang „beschränkt“ nach einem abschließbaren Gehäuse. Liegt es noch über „niedrig“, braucht es eine weitere Maßnahme oder eine Akzeptanz mit Freigabe.',
    },
    en: {
      title: 'Residual risk',
      text: 'The risk that remains once the measures are in place. Rate environment and impact as if the measure were already effective, e.g. access "restricted" after a lockable housing. If it is still above "low", you need another measure or an approved acceptance.',
    },
  },
  acceptance: {
    de: {
      title: 'Akzeptanz',
      text: 'Sie entscheiden bewusst, ein Risiko über „niedrig“ zu tragen, z. B. weil eine Maßnahme unverhältnismäßig wäre. Dafür braucht es eine Begründung und eine Freigabe durch die Rolle, die die Methode für diese Risikostufe vorsieht.',
    },
    en: {
      title: 'Acceptance',
      text: 'You consciously decide to carry a risk above "low", e.g. because a measure would be disproportionate. It needs a rationale and approval by the role the method requires for that risk level.',
    },
  },
  compensating: {
    de: {
      title: 'Kompensierende Maßnahme',
      text: 'Eine Maßnahme, die eine Anforderung auf anderem Weg erfüllt, weil der übliche Weg nicht geht, z. B. Netztrennung statt Verschlüsselung bei einem Feldbus ohne Kryptografie.',
    },
    en: {
      title: 'Compensating measure',
      text: 'A measure that meets a requirement another way because the usual way is not possible, e.g. network segregation instead of encryption on a fieldbus without cryptography.',
    },
  },
  coverage: {
    de: {
      title: 'Abdeckung',
      text: 'Für jedes Element und jeden Datenfluss eine Zeile, für jeden STRIDE-Buchstaben eine Spalte. Ein Feld ist abgedeckt, wenn es dazu eine Bedrohung gibt oder wenn Sie es als „nicht relevant“ (n. r.) markiert haben. Leere Felder sind Lücken, die die Prüfung meldet.',
    },
    en: {
      title: 'Coverage',
      text: 'One row per element and data flow, one column per STRIDE letter. A cell is covered if a threat exists for it or you marked it "not relevant" (n/r). Empty cells are gaps that validation reports.',
    },
  },
} satisfies Record<string, Entry>

export type Term = keyof typeof GLOSSARY

/** The question behind each STRIDE letter, shown next to the category. */
export const STRIDE_QUESTIONS: Record<Lang, Record<string, string>> = {
  de: {
    S: 'Kann sich jemand als dieses Element ausgeben?',
    T: 'Kann jemand Daten, Befehle oder Software verändern?',
    R: 'Kann jemand eine Aktion abstreiten, weil sie nicht nachweisbar ist?',
    I: 'Können Daten abfließen?',
    D: 'Kann jemand die Funktion stören oder lahmlegen?',
    E: 'Kann jemand mehr Rechte erlangen, als er haben darf?',
  },
  en: {
    S: 'Can someone pretend to be this element?',
    T: 'Can someone change data, commands or software?',
    R: 'Can someone deny an action because it is not traceable?',
    I: 'Can data leak?',
    D: 'Can someone disrupt or stop the function?',
    E: 'Can someone gain more rights than allowed?',
  },
}

/** Form field keys that share an explanation with a glossary term. */
const FIELD_TERMS: Record<string, Term> = {
  zone: 'zone',
  configurations: 'configurations',
  kind: 'kind',
  asset_class: 'asset_class',
  assets: 'asset_class',
  protects: 'protects',
  stride: 'stride',
  cyber_cause: 'cyber_cause',
  'amplifier.c': 'amplifier',
  'amplifier.i': 'amplifier',
  'amplifier.a': 'amplifier',
  'acceptance.by': 'acceptance',
  compensating: 'compensating',
}

export const termForField = (collection: string, key: string): Term | undefined =>
  key === 'kind' && collection !== 'elements' ? undefined : FIELD_TERMS[key]
