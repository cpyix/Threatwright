"""Example projects per product type, built from the library building blocks.

`threatwright init --example` and the GUI fill the new project's main model with a
small, neutral demo: elements and flows from the library, adopted threats with
their measures, some assessed, one measure implemented and one risk accepted.
Everything is marked as an example; no real product data.
"""

import datetime
from dataclasses import dataclass
from typing import Literal

from threatwright import assistant
from threatwright.library import load_libraries
from threatwright.method import Method, evaluate, load_method
from threatwright.model.objects import Asset, ChangelogEntry, Decision, Flow, Measure, Threat
from threatwright.model.store import Project

Lang = Literal["de", "en"]


@dataclass(frozen=True)
class Example:
    title: tuple[str, str]  # de, en
    description: tuple[str, str]
    # key: (library type, zone, title de, title en)
    elements: dict[str, tuple[str, str, str, str]]
    flows: list[tuple[str, str, str]]  # source key, target key, flow type
    adopt: dict[str, int]  # element key: first n suggestions
    # zone: (access, user); the interface comes from the project template
    environment: dict[str, tuple[str, str]]


EXAMPLES: dict[str, Example] = {
    "ot": Example(
        ("Beispielmaschine", "Example machine"),
        (
            "Beispielmodell aus den Bausteinen der OT-Bibliothek: Steuerung, Antrieb, "
            "Bedienpanel, Engineering-Rechner und Fernwartung.",
            "Example model from the OT library building blocks: controller, drive, operator "
            "panel, engineering workstation and remote service.",
        ),
        {
            "plc": ("plc", "Z-INTERNAL", "Maschinensteuerung", "Machine controller"),
            "drive": ("drive", "Z-INTERNAL", "Achsantrieb", "Axis drive"),
            "hmi": ("hmi", "Z-LOCAL", "Bedienpanel", "Operator panel"),
            "ews": (
                "engineering-workstation",
                "Z-PLANT",
                "Engineering-Rechner",
                "Engineering workstation",
            ),
            "gw": (
                "remote-access-gateway",
                "Z-EXTERNAL",
                "Fernwartungs-Gateway",
                "Remote service gateway",
            ),
        },
        [
            ("hmi", "plc", "ip-network"),
            ("plc", "drive", "fieldbus-ethercat"),
            ("ews", "plc", "ip-network"),
            ("gw", "ews", "vpn-tunnel"),
        ],
        {"plc": 3, "hmi": 2, "gw": 2},
        {
            "Z-INTERNAL": ("restricted", "non_user_related"),
            "Z-LOCAL": ("public_restricted", "instructed"),
            "Z-PLANT": ("restricted", "skilled"),
            "Z-EXTERNAL": ("non_restricted", "skilled"),
        },
    ),
    "iot": Example(
        ("Beispielgerät", "Example device"),
        (
            "Beispielmodell aus den Bausteinen der IoT-Bibliothek: vernetztes Gerät mit "
            "Firmware, Begleit-App, Hersteller-Cloud und Update-Dienst.",
            "Example model from the IoT library building blocks: connected device with "
            "firmware, companion app, vendor cloud and update service.",
        ),
        {
            "dev": ("iot-device", "Z-INTERNAL", "Smarter Sensor", "Smart sensor"),
            "fw": ("iot-firmware", "Z-INTERNAL", "Geräte-Firmware", "Device firmware"),
            "app": ("companion-app", "Z-LAN", "Begleit-App", "Companion app"),
            "cloud": ("vendor-cloud", "Z-EXTERNAL", "Hersteller-Cloud", "Vendor cloud"),
            "ota": ("ota-service", "Z-EXTERNAL", "Update-Dienst", "Update service"),
        },
        [
            ("app", "dev", "flow-ble"),
            ("dev", "cloud", "flow-mqtt-tls"),
            ("app", "cloud", "flow-https-cloud"),
            ("ota", "fw", "flow-https-cloud"),
        ],
        {"dev": 2, "fw": 2, "cloud": 2},
        {
            "Z-INTERNAL": ("restricted", "non_user_related"),
            "Z-LOCAL": ("movable", "layman"),
            "Z-LAN": ("public_restricted", "layman"),
            "Z-EXTERNAL": ("non_restricted", "skilled"),
        },
    ),
    "software": Example(
        ("Beispielanwendung", "Example application"),
        (
            "Beispielmodell aus den Bausteinen der Software-Bibliothek: Desktop-Anwendung "
            "mit lokaler Datenbank, Backend-API und Updater.",
            "Example model from the software library building blocks: desktop application "
            "with local database, backend API and updater.",
        ),
        {
            "user": ("app-user", "Z-LOCAL", "Anwender", "User"),
            "app": ("desktop-app", "Z-INTERNAL", "Desktop-Anwendung", "Desktop application"),
            "db": ("local-database", "Z-INTERNAL", "Lokale Datenbank", "Local database"),
            "api": ("backend-api", "Z-EXTERNAL", "Backend-API", "Backend API"),
            "upd": ("updater", "Z-INTERNAL", "Updater", "Updater"),
        },
        [
            ("user", "app", "flow-ipc"),
            ("app", "db", "flow-file-exchange"),
            ("app", "api", "flow-https-api"),
            ("api", "upd", "flow-https-api"),
        ],
        {"app": 3, "api": 2, "upd": 1},
        {
            "Z-INTERNAL": ("restricted", "non_user_related"),
            "Z-LOCAL": ("public_restricted", "layman"),
            "Z-LAN": ("public_restricted", "layman"),
            "Z-EXTERNAL": ("non_restricted", "skilled"),
        },
    ),
}


def _security(method: Method, asset: Asset) -> bool:
    cls = method.asset_classes.get(asset.asset_class)
    return cls is not None and any(isinstance(v, list) for v in (cls.c, cls.i, cls.a))


def fill_example(project: Project, kind: str, today: datetime.date | None = None) -> None:
    """Fill the main model of a freshly created `tr` project with the example of `kind`."""
    example = EXAMPLES[kind]
    today = today or datetime.date.today()
    lang: Lang = project.config.language
    de = lang == "de"
    libs = load_libraries(project.config.libraries, project.root)
    method = load_method(project.root, project.config)
    sub = project.models["main"]
    sub.meta.title = example.title[0 if de else 1]
    sub.meta.description = example.description[0 if de else 1]
    for zone in sub.meta.zones:
        if zone.id in example.environment:
            access, user = example.environment[zone.id]
            zone.environment = zone.environment.model_copy(update={"access": access, "user": user})
    sub.meta.changelog = [
        ChangelogEntry(
            version="0.1",
            date=today,
            summary="Beispielprojekt angelegt" if de else "Example project created",
        )
    ]

    ids: dict[str, str] = {}
    plain: dict[str, list[str]] = {}  # element id -> its assets that are not security assets
    owner: dict[str, str] = {}  # security asset -> element it came with
    zone_row = {z.id: n for n, z in enumerate(sub.meta.zones)}
    for n, (key, (etype, zone_id, t_de, t_en)) in enumerate(example.elements.items()):
        position = (40.0 + n * 220, 40.0 + zone_row.get(zone_id, 0) * 160)
        before = set(sub.objects["assets"])
        element = assistant.add_element(
            sub, libs, project.config, etype, t_de if de else t_en, zone_id, position
        )
        ids[key] = element.id
        # security assets (keys, logs) inherit their impact from what they protect
        new = [a for i, a in sub.objects["assets"].items() if i not in before]
        plain[element.id] = [a.id for a in new if isinstance(a, Asset) and not _security(method, a)]
        for a in new:
            if isinstance(a, Asset) and _security(method, a):
                a.protects = plain[element.id]
                owner[a.id] = element.id
    for source, target, ftype in example.flows:
        flow = assistant.add_flow(sub, libs, project.config, ids[source], ids[target], ftype)
        ends = plain[ids[source]] + plain[ids[target]]
        for asset_id in flow.assets:  # e.g. the keys of a VPN tunnel protect both ends
            a = sub.objects["assets"][asset_id]
            if isinstance(a, Asset) and _security(method, a):
                a.protects = [x for x in flow.assets if x != asset_id and x not in ends] + ends
    # an element with security assets only (e.g. an updater) protects its neighbours
    ends_of = [(f.source, f.target) for f in sub.objects["flows"].values() if isinstance(f, Flow)]
    for asset_id, element_id in owner.items():
        a = sub.objects["assets"][asset_id]
        if isinstance(a, Asset) and not a.protects:
            near = {e for pair in ends_of if element_id in pair for e in pair} - {element_id}
            a.protects = [x for e in sorted(near) for x in plain.get(e, [])]

    for key, count in example.adopt.items():
        cats = assistant.suggestions(sub, libs, method, project.config, ids[key])
        templates = [
            s.template_id
            for c in cats.values()
            for s in c.suggestions
            if libs.threats[s.template_id].measures  # every example threat gets a measure
        ]
        for template in list(dict.fromkeys(templates))[:count]:
            assistant.adopt_threat(sub, libs, project.config, template, ids[key])

    threats = [t for t in sub.objects["threats"].values() if isinstance(t, Threat)]
    for t in threats:
        if None not in (t.assessment.interface, t.assessment.access, t.assessment.user):
            t.assessment.impact = t.assessment.impact or 3
            t.status = "assessed"
    acceptable = [t for t in threats if evaluate(method, t, project.config).acceptable]
    if not acceptable and threats:  # lowest impact makes one threat acceptable for the demo
        threats[-1].assessment.impact = 1
        acceptable = [t for t in threats[-1:] if evaluate(method, t, project.config).acceptable]
    if acceptable:  # show a documented acceptance
        t = acceptable[0]
        t.status = "accepted"
        t.acceptance = Decision(
            by="Beispiel" if de else "Example",
            role="Produktverantwortung" if de else "Product owner",
            date=today,
            rationale="Beispiel: Risiko liegt unter der Akzeptanzgrenze."
            if de
            else "Example: the risk is below the acceptance limit.",
        )
    measures = [m for m in sub.objects["measures"].values() if isinstance(m, Measure)]
    if measures:  # show an implemented measure with evidence
        m = measures[0]
        m.status = "implemented"
        m.evidence = "Beispiel: Prüfbericht" if de else "Example: test report"
    project.config.support_until = today.replace(year=today.year + 5, day=min(today.day, 28))
    project.config.next_review = today.replace(year=today.year + 1, day=min(today.day, 28))
