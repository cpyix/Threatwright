# Quick start (10 minutes)

*This is the English version of [../schnellstart.md](../schnellstart.md) (German).*

## 1. Install

You have three options:

- **Portable version (recommended):** download the ZIP for Windows or the `tar.gz` for Linux from the release page, unpack it and start `threatwright`. You need neither Python nor administrator rights. There is no portable version for macOS; use the Python variant there.
- **With Python:** `pipx install threatwright`
- **For CI:** the container image, see [ci.md](../ci.md) (German)

## 2. Create a project

```
threatwright init mein-produkt --name "Mein Produkt"
```

Choose the product type with `--library` (short `-l`): `ot` (machines and plants, default), `iot` (connected devices, consumer), `software` or `embedded-linux` (control software on a Linux industrial PC, brings `ot` along; the example creates a machine model and a sub-model `software`). The option can be repeated, e.g. `-l iot -l software`. In the GUI you choose the product type with a checkbox on the start page when creating a project.

The tool creates a folder with a submodel `main`. It contains:
- four default zones: device internal, local interfaces, plant network, external network. Without `ot`, the third zone is called "Local network (LAN/WLAN)" (Z-LAN).
- the chosen library or libraries, `ot` if none is given
- the file `method-overrides.yaml` with all decision points for risk acceptance

It is best to make the folder a Git repository right away (`git init`).

**Want to try it first?** `threatwright init example -l iot --example` creates a small ready-made example model of that product type (elements, connections, assessed threats, measures, one acceptance). In the GUI the checkbox is called "With example model".

## 3. Start the GUI

```
threatwright --project mein-produkt
```

Your default browser opens. The GUI runs only on your machine at `127.0.0.1` and makes no connections to the internet.

## 4. Build the model

**With the setup wizard (recommended to get started):** A project newly created in the GUI opens the wizard directly. For existing projects, open it via **Setup** in the navigation. It leads through eight steps: product description and intended use, an optional CRA classification (for orientation only, nothing is saved, not in the report), zones with interface, access and user, components from the library, connections, assets with TR class, threat suggestions (these count as cyber risks under rule 3.3) and a final overview. The guiding questions depend on the product type; further libraries can be added in the product step (not removed); an added library is saved with the project (Ctrl+S) and cannot be reverted with Ctrl+Z. Everything ends up as normal model content in the project; Undo and Save work as everywhere else.

**By hand** in the individual views:

1. **Diagram:** Drag building blocks from the list on the left onto the canvas, e.g. "Industrial PC Linux", "Drive controller / servo amplifier", "HMI / operator panel". The tool creates the typical assets of each building block at the same time.
2. **Connections:** Choose the type at the top, e.g. "EtherCAT", then drag from a connection point of one element to another.
3. **Zones:** Click an element and set the zone on the right. The zone sets the environment for the assessment.
4. **STRIDE assistant:** In the right-hand panel, click "STRIDE assistant →". Suggestions from the library appear for each category; "Adopt" creates a prefilled threat with matching measures.
5. **"Is the cause an attack on the digital product?":** This question appears for every new threat. If the answer is "No, other cause", the entry is rejected with a rationale.
6. **Assess:** Under "Threats", check the assessment, that is interface, access, user and impact. Risk and "acceptable / to be treated" appear immediately.
7. **Coverage:** The matrix shows gaps per element and STRIDE category. You close a gap through the assistant or with "n/r" (not relevant) and a rationale.
8. **Validation:** Open issues are listed; a click jumps to the affected object.
9. **Save:** Ctrl+S. Every object is its own YAML file; you commit them with your Git tool.

## 5. Generate a document

```
threatwright build mein-produkt --format docx
```

The file ends up in `mein-produkt/build/`. Custom templates are described in the [template reference](../vorlagenreferenz.md) (German).

## 6. Check in the pipeline

Under **Settings → CI pipeline** there is a ready-made GitLab template for your project to copy. Alternatively, `threatwright ci gitlab mein-produkt` prints it. Continue with the [tutorial](tutorial.md).
