"""Example projects per product type, built from the library building blocks.

`threatwright init --example` and the GUI fill the new project's main model with a
small, neutral demo: elements and flows from the library, adopted threats with
their measures, some assessed, one measure implemented and one risk accepted.
Everything is marked as an example; no real product data.
"""

import datetime
from dataclasses import dataclass, field
from typing import Literal

from threatwright import assistant
from threatwright.library import Libraries, load_libraries
from threatwright.method import Method, evaluate, load_method
from threatwright.model.objects import (
    Asset,
    ChangelogEntry,
    Decision,
    Element,
    Flow,
    Listener,
    Measure,
    ModelMeta,
    Threat,
)
from threatwright.model.store import Project, SubModel

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
    hosts: dict[str, str] = field(default_factory=dict)  # element key: key of its host (runs_on)
    listens: dict[str, list[dict[str, object]]] = field(default_factory=dict)  # listens_on


@dataclass(frozen=True)
class SubExample:
    """A sub-model refining one element of the main model (one assessment per product)."""

    name: str
    example: Example
    refines: tuple[str, str]  # (key in the sub-model, key in the main model)


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
    "embedded-linux": Example(
        (
            "Beispielmaschine mit Linux-Steuerungsrechner",
            "Example machine with Linux industrial PC",
        ),
        (
            "Beispielmodell: Maschine mit Linux-Steuerungsrechner, Antrieb, Bedienpanel und "
            "Engineering-Rechner. Die Software auf dem Steuerungsrechner ist im Teilmodell "
            "„software“ verfeinert.",
            "Example model: machine with Linux industrial PC, drive, operator panel and "
            "engineering workstation. The software on the industrial PC is refined in the "
            "sub-model 'software'.",
        ),
        {
            "ipc": ("ipc-linux", "Z-PLANT", "Steuerungsrechner", "Industrial PC"),
            "drive": ("drive", "Z-INTERNAL", "Achsantrieb", "Axis drive"),
            "hmi": ("hmi", "Z-LOCAL", "Bedienpanel", "Operator panel"),
            "ews": (
                "engineering-workstation",
                "Z-PLANT",
                "Engineering-Rechner",
                "Engineering workstation",
            ),
        },
        [
            ("hmi", "ipc", "ip-network"),
            ("ipc", "drive", "fieldbus-ethercat"),
            ("ews", "ipc", "ip-network"),
        ],
        {"drive": 2, "hmi": 2, "ews": 1},
        {
            "Z-INTERNAL": ("restricted", "non_user_related"),
            "Z-LOCAL": ("public_restricted", "instructed"),
            "Z-PLANT": ("restricted", "skilled"),
            "Z-EXTERNAL": ("non_restricted", "skilled"),
        },
    ),
}

SUBMODELS: dict[str, SubExample] = {
    "embedded-linux": SubExample(
        "software",
        Example(
            ("Steuerungssoftware (Beispiel)", "Control software (example)"),
            (
                "Teilmodell des Steuerungsrechners: Prozesse mit ihren Rechten, lokale Dienste, "
                "Shared Memory, Kernel und Update-Bereitstellung.",
                "Sub-model of the industrial PC: processes with their rights, local services, "
                "shared memory, kernel and update staging.",
            ),
            {
                "host": ("ipc-linux", "Z-PLANT", "Steuerungsrechner", "Industrial PC"),
                "rt": ("lx-rt-control", "", "Echtzeit-Steuerung", "Real-time control"),
                "fb": ("lx-fieldbus-master", "", "Feldbus-Master", "Fieldbus master"),
                "ui": ("lx-local-hmi", "", "Lokale Bedienoberfläche", "Local operator UI"),
                "svc": ("lx-network-daemon", "", "Diagnosedienst", "Diagnostics service"),
                "sshd": ("lx-os-service", "", "SSH-Dienst", "SSH service"),
                "kernel": ("lx-kernel", "", "Linux-Kernel mit RT-Erweiterung", "Linux kernel (RT)"),
                "kmod": ("lx-kernel-module", "", "Feldbus-Treiber", "Fieldbus driver"),
                "shm": (
                    "lx-shared-memory",
                    "Z-PLANT",
                    "Prozessabbild (Shared Memory)",
                    "Process image (shared memory)",
                ),
                "staging": (
                    "lx-update-staging",
                    "Z-PLANT",
                    "Update-Bereitstellung",
                    "Update staging",
                ),
                "tech": (
                    "lx-service-technician",
                    "Z-PLANT",
                    "Servicetechniker",
                    "Service technician",
                ),
            },
            [
                ("ui", "rt", "lx-local-ipc"),
                ("svc", "rt", "lx-local-ipc"),
                ("rt", "shm", "lx-local-ipc"),
                ("fb", "shm", "lx-local-ipc"),
                ("tech", "sshd", "lx-remote-shell"),
            ],
            {"rt": 2, "svc": 2, "ui": 1, "kmod": 1, "shm": 1},
            {},
            hosts={k: "host" for k in ("rt", "fb", "ui", "svc", "sshd", "kernel", "kmod")},
            listens={
                "svc": [{"protocol": "tcp", "port": 5000, "interfaces": "all"}],
                "sshd": [{"protocol": "tcp", "port": 22, "interfaces": "all"}],
                "ui": [{"protocol": "unix", "path": "/run/control/ui.sock"}],
            },
        ),
        ("host", "ipc"),
    ),
}


def _security(method: Method, asset: Asset) -> bool:
    cls = method.asset_classes.get(asset.asset_class)
    return cls is not None and any(isinstance(v, list) for v in (cls.c, cls.i, cls.a))


def fill_example(project: Project, kind: str, today: datetime.date | None = None) -> None:
    """Fill the main model of a freshly created `tr` project with the example of `kind`,
    plus the sub-model that refines one of its elements, if the product type has one."""
    today = today or datetime.date.today()
    libs = load_libraries(project.config.libraries, project.root)
    method = load_method(project.root, project.config)
    main = project.models["main"]
    ids = _fill(project, main, EXAMPLES[kind], libs, method, today)
    part = SUBMODELS.get(kind)
    if part is None:
        return
    sub = SubModel(part.name, ModelMeta(title=part.name))
    sub.meta.zones = [z.model_copy(deep=True) for z in main.meta.zones]  # same environment
    sub.meta.configurations = [c.model_copy() for c in main.meta.configurations]
    project.models[part.name] = sub
    sub_ids = _fill(project, sub, part.example, libs, method, today)
    host = sub.objects["elements"][sub_ids[part.refines[0]]]
    if isinstance(host, Element):
        host.refines = f"{main.name}/{ids[part.refines[1]]}"


def _fill(
    project: Project,
    sub: SubModel,
    example: Example,
    libs: Libraries,
    method: Method,
    today: datetime.date,
) -> dict[str, str]:
    """Elements, flows, adopted and assessed threats of one model; returns key -> element id."""
    lang: Lang = project.config.language
    de = lang == "de"
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
        host = ids.get(example.hosts.get(key, ""))
        element = assistant.add_element(
            sub, libs, project.config, etype, t_de if de else t_en, zone_id or None, position, host
        )
        element.listens_on = [Listener.model_validate(x) for x in example.listens.get(key, [])]
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
    return ids
