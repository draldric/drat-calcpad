# Compatibility matrix

The release manifest is the machine-readable compatibility authority.
This table summarizes the currently supported package combination.

| Package | Version or API | Requires |
| --- | ---: | --- |
| DRAT generated Core | 4.1.2 / `40102` | CalcPad CE worksheet evaluation |
| Definitions | `20000` | Bundled with Core 4.1.2 |
| Stylesheet | `10800` | Bundled with Core 4.1.2 |
| DataWrapper | `303` | Bundled with Core 4.1.2 |
| Engineering Checks | `20000` | Bundled with Core 4.1.2 |
| Check Registry | `10000` | Bundled with Core 4.1.2 |
| Database | `10000` | Bundled with Core 4.1.2 |
| Validation | `20000` | Bundled with Core 4.1.2 |
| Calculation Status | `20000` | Bundled with Core 4.1.2 |
| Reporting | `20001` | Bundled with Core 4.1.2 |
| Review Summary | `10000` | Bundled with Core 4.1.2 |
| Plotting | `30200` | Bundled with Core 4.1.2 and network access for Plotly |
| Engineering Materials | 1.4.0 | Core `10000–49999`, DataWrapper `302–999`, Plotting `30200–39999` |

Library compatibility guards are evaluated by CalcPad when the library is loaded.
An incompatible library skips its body and renders a load error instead of continuing with undefined or incompatible helpers.
