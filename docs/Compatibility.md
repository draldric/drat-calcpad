# Compatibility matrix

The release manifest is the machine-readable compatibility authority.
This table summarizes the currently supported package combination.

| Package | Version or API | Requires |
| --- | ---: | --- |
| DRAT generated Core | 4.3.0 / `40300` | CalcPad CE worksheet evaluation |
| Definitions | `20200` | Bundled with Core 4.3.0 |
| Stylesheet | `11000` | Bundled with Core 4.3.0 |
| DataWrapper | `303` | Bundled with Core 4.3.0 |
| Engineering Checks | `20000` | Bundled with Core 4.3.0 |
| Check Registry | `10100` | Bundled with Core 4.3.0 |
| Database | `10000` | Bundled with Core 4.3.0 |
| Validation | `20100` | Bundled with Core 4.3.0 |
| Calculation Status | `20000` | Bundled with Core 4.3.0 |
| Reporting | `20100` | Bundled with Core 4.3.0 |
| Authoring | `10000` | Bundled with Core 4.3.0 |
| Review Summary | `10100` | Bundled with Core 4.3.0 |
| Plotting | `30200` | Bundled with Core 4.3.0 and network access for Plotly |
| Engineering Materials | 1.4.0 | Core `10000–49999`, DataWrapper `302–999`, Plotting `30200–39999` |
| Beam Analysis | 0.6.0 | Core `10000–49999`, DataWrapper `302–999`, Checks `10200–29999`; Plotting `30200–39999` is optional and gates diagram helpers |
| Thermophysical Properties | 0.1.0 | Core `40000–49999`, DataWrapper `303–999` |
| AISC W Shapes | 0.1.0 | Core `10000–49999`, DataWrapper `302–999` |
| AISC HSS | 0.1.0 | Core `10000–49999`, DataWrapper `302–999` |
| AISC Channels | 0.1.0 | Core `10000–49999`, DataWrapper `302–999` |
| AISC Single Angles | 0.1.0 | Core `10000–49999`, DataWrapper `302–999` |

Library compatibility guards are evaluated by CalcPad when the library is loaded.
An incompatible library skips its body and renders a load error instead of continuing with undefined or incompatible helpers.
Distribution manifest schema 2 records mandatory guards under each library's `requirements` object and feature-specific guards under `optional_requirements`.
The installer and qualification test compare those ranges, component APIs, versions, library identities, and revisions against the packaged CalcPad declarations.
