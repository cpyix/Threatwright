# Tutorial: "Fieldbus" submodel in 30 minutes

*This is the English version of [../tutorial.md](../tutorial.md) (German).*

In this tutorial you build a submodel for the fieldbus of a product. The product is neutral and entirely fictional:

- a control computer running Linux as fieldbus master
- two drive controllers
- a remote I/O module in the machine area
- outputs with safety effect that are switched by the software

The tutorial uses the product type OT (default). For a connected device or a piece of software, create the project with `-l iot` or `-l software`; the procedure stays the same, only the building blocks and guiding questions differ.

Plan for about 30 minutes. The times are rough guides.

## Preparation (2 min)

```
threatwright init feldbus-tutorial --name "Tutorial"
cd feldbus-tutorial
git init
threatwright
```

In the setup wizard there is the optional step **CRA classification** before the zones. It is for orientation, saves nothing and does not appear in the report; you can skip it for the tutorial.

## 1. Check the zones (3 min)

Open **Overview** and scroll to **Zones and trust boundaries**. The four default zones are enough for the tutorial. Their meaning:

| Zone | Interface | Meaning |
|---|---|---|
| Z-INTERNAL | physical | reachable only by opening the device |
| Z-LOCAL | local | interfaces on the device (USB, service port, fieldbus socket) |
| Z-PLANT | known network | the operator's plant network |
| Z-EXTERNAL | external network | internet, remote maintenance |

In the same table, set access and user per zone and click **Apply**. For the control cabinet, for example, access is "restricted".

## 2. Drag elements into the diagram (5 min)

Under **Diagram**, drag from the list on the left:

1. "Industrial PC Linux", then choose the zone Z-LOCAL on the right
2. "Drive controller / servo amplifier", twice
3. "Remote I/O / bus coupler"
4. "Outputs with safety effect"

Each element brings its typical assets, for example "Drive parameters" with the TR class `Other.Configuration`.

## 3. Connect the fieldbus (3 min)

At the top, choose **Type of new connections: EtherCAT**. Then drag a connection from the control computer to each drive and to the remote I/O. "Auto layout" arranges the diagram.

## 4. Threats with the assistant (10 min)

Click the first EtherCAT data flow and open **STRIDE assistant →**. For T, I and D, adopt the matching suggestions:

- foreign master on the fieldbus
- device looped in
- open port at the end of the line
- parameter access via the mailbox
- EoE tunnel
- fieldbus overload

Each suggestion describes an attack and therefore counts as a cyber risk (rule 3.3) when adopted. If one does not fit after all, reject it under **Threats** with a rationale.

Repeat this for the drive controllers (parameter manipulation, firmware download over the bus) and for the outputs with safety effect. The adopted measures appear only once under **Measures**, even if several threats suggest them.

## 5. Assess (5 min)

Under **Threats**, open each entry:

- Interface and access are prefilled from the template and the zone. Check whether they are right for your product.
- Take over the impact via the suggestion from the assets, or set it differently on purpose. Then write a rationale.
- Risk and "acceptable / to be treated" appear immediately. Note: the matrix is read "inverted", see [Methodology](../methodik.md) (German).
- Set the status to "treated" when an agreed measure lowers the risk. Enter the assessment after the measures in the field **Residual risk after measures**.

## 6. Coverage and validation (2 min)

Under **Coverage**, gaps are marked. Close each gap, either with "+" via the assistant or with "n/r" and a rationale. Under **Validation** there should be no errors left.

## 7. Save, commit, generate a document

Save with **Ctrl+S** and then commit:

```
git add . && git commit -m "Teilmodell Feldbus"
threatwright build --format docx
```

For a release, set a tag (`git tag v1.0`). Later, `threatwright diff v1.0` shows what has changed in substance since then, as proof of change; see [Git workflow](../git-arbeitsweise.md) (German). In the GUI, **Changes (Git)** shows the same, also before saving.

## 8. For the CRA documentation (optional)

- **CRA requirements:** shows, for each essential requirement of Annex I, which threats and measures cover it. Mark what does not apply to your product as not applicable, with a rationale.
- **Vulnerabilities:** upload the SBOM of the control software (CycloneDX JSON) and assign it to the element. Vulnerability statements (VEX, CSAF) show which component is affected; every affecting vulnerability needs a threat ([SBOM and vulnerabilities](../sbom.md), German).
- **Approvals:** accepted risks get a name, role and date. The report lists them with the Git revision in the section "Approvals".
- **Evidence:** implemented measures get evidence as text, a file (copied to `evidence/`) or a link.
- **Settings → Product and lifecycle:** support period and next review of the model.
