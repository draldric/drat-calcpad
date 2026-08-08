# CalcpadCE Engineering Framework

Modular framework for reusable engineering calculations.

## Core and libraries

Worksheets load the generated core bundle before any optional libraries:

```text
#include ../Core/DratCore.cpd
#include ../Libraries/Materials/EngineeringMaterials.cpd
```

Maintain the individual core modules in `Core/Src/`.
Run `Tools/BuildCore.ps1` after changing a core source module, and commit the regenerated `Core/DratCore.cpd`.
Run `Tools/BuildCore.ps1 -Check` to verify that the committed bundle is current.

Libraries do not include their own dependencies.
Each library checks the core API and its required component APIs before loading its definitions.
If a required API is missing or incompatible, the library skips its body and renders a compatibility error.
