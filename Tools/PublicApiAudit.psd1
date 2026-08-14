@{
    # Every module containing multiline macro assignments owns one local prefix.
    # Paths use repository-relative forward slashes for deterministic comparison.
    MacroLocalPrefixes = @{
        'Core/Src/CalculationStatus.cpd' = 'CALC'
        'Core/Src/CheckRegistry.cpd' = 'CHECK'
        'Core/Src/Plotting.cpd' = 'PLOT'
        'Core/Src/Reporting.cpd' = 'RPT'
        'Core/Src/ReviewSummary.cpd' = 'REVIEW'
        'Core/Src/Validation.cpd' = 'VAL'
        'Libraries/Analysis/BeamAnalysis.cpd' = 'BEAM'
        'Libraries/Materials/EngineeringMaterials.cpd' = 'MAT'
        'Libraries/Steel/AiscAngleSections.cpd' = 'AISC'
        'Libraries/Steel/AiscChannelSections.cpd' = 'AISC'
        'Libraries/Steel/AiscHssSections.cpd' = 'AISC'
        'Libraries/Steel/StructuralSections.cpd' = 'AISC'
    }

    # These assignments intentionally update worksheet-global registries.
    # All other assignments inside macros must use the owning module prefix.
    ApprovedGlobalMacroAssignments = @{
        'EngineeringCheckRegistry' = @{
            Source = 'Core/Src/CheckRegistry.cpd'
            Macros = @('AddCheckResult$')
            Purpose = 'Stores successfully registered engineering checks for document aggregation.'
        }
        'EngineeringCheckRegistryErrors' = @{
            Source = 'Core/Src/CheckRegistry.cpd'
            Macros = @('AddCheckResult$')
            Purpose = 'Stores every engineering-check registration result for integrity reporting.'
        }
        'InputValidationRegistry' = @{
            Source = 'Core/Src/Validation.cpd'
            Macros = @('AddValidationResult$')
            Purpose = 'Stores successfully registered input validations for document aggregation.'
        }
        'InputValidationRegistryErrors' = @{
            Source = 'Core/Src/Validation.cpd'
            Macros = @('AddValidationResult$')
            Purpose = 'Stores every input-validation registration result for integrity reporting.'
        }
        'ReportReferences' = @{
            Source = 'Core/Src/Reporting.cpd'
            Macros = @('AddReference$')
            Purpose = 'Stores registered document references.'
        }
        'ReportDesignCriteria' = @{
            Source = 'Core/Src/Reporting.cpd'
            Macros = @('AddDesignCriterion$')
            Purpose = 'Stores registered design criteria and their reference links.'
        }
        'ReportAssumptions' = @{
            Source = 'Core/Src/Reporting.cpd'
            Macros = @('AddAssumption$')
            Purpose = 'Stores registered assumptions and their optional reference links.'
        }
        'ReportLimitations' = @{
            Source = 'Core/Src/Reporting.cpd'
            Macros = @('AddLimitation$')
            Purpose = 'Stores registered limitations and their optional reference links.'
        }
        'ReportRegistryErrors' = @{
            Source = 'Core/Src/Reporting.cpd'
            Macros = @('AddReference$', 'AddDesignCriterion$', 'AddAssumption$', 'AddLimitation$')
            Purpose = 'Stores every reporting-registry attempt for integrity reporting and source links.'
        }
    }

    # These helpers support public implementations but are not part of the worksheet API.
    # Keep the reason beside the name so an exception cannot become unexplained debt.
    InternalHelpers = @{
        'CalculationValidationKnownCount' = 'Counts recognized validation statuses for CalculationValidationStatusesOK.'
        'CheckMethodKnown' = 'Validates the private method discriminator stored in check-result rows.'
        'CheckResultColumn' = 'Provides bounds-safe column access for the public check-result accessors.'
        'CheckResultIDOK' = 'Validates IDs while adding check-result records.'
        'CheckRegistryID$' = 'Renders the anchor content used by check-registry report macros.'
        'CheckRegistryLink$' = 'Renders internal links used by check-registry summaries.'
        'CheckRegistryStatus$' = 'Renders check-registry mutation errors inside higher-level macros.'
        'ReportEntryType$' = 'Renders internal reporting-registry type labels.'
        'ReportEntryTypeKnown' = 'Validates internal reporting-registry type discriminators.'
        'ReportErrorRecord' = 'Builds the private attempted-registration row format.'
        'ReportID$' = 'Renders reporting-registry anchors inside higher-level macros.'
        'ReportReferenceID$' = 'Renders optional reference IDs inside higher-level macros.'
        'ReportReferenceIDOK' = 'Validates optional source IDs while adding reporting records.'
        'ValidationRegistryID$' = 'Renders the anchor content used by validation-registry report macros.'
        'ValidationRegistryLink$' = 'Renders internal links used by validation issue summaries.'
        'ValidationRegistryStatus$' = 'Renders validation-registry mutation errors inside higher-level macros.'
        'ValidationResultRecordIDOK' = 'Validates IDs while adding validation-result records.'
        'ValidationResultRegistryValues' = 'Provides bounds-safe column access for public validation-registry accessors.'
    }

    # These are deliberate worksheet-facing extension points. They may have no call site
    # in maintained code, but each must retain an exact documentation or demo reference.
    DefinitionOnlyPublicHelpers = @{
        'AddListItem$' = 'Adds one item to a caller-owned reusable list section.'
        'annotate$' = 'Adds a caller-defined annotation to a Plotly figure.'
        'area$' = 'Adds a filled-area trace to a Plotly figure.'
        'bar$' = 'Adds a bar trace to a Plotly figure.'
        'barMode$' = 'Selects the Plotly bar grouping mode.'
        'BeginListSection$' = 'Begins a caller-owned reusable list section.'
        'CheckIsFailure' = 'Lets worksheets classify one check status without building an aggregate.'
        'CheckIsPass' = 'Lets worksheets test one check status for a pass.'
        'CheckIsWarning' = 'Lets worksheets test one check status for a warning.'
        'cmt$' = 'Supports imported worksheet patterns that emit HTML comments.'
        'DBIsWarning' = 'Lets property libraries distinguish warning lookup statuses.'
        'DRATCoreName$' = 'Publishes the display name of the loaded Core bundle.'
        'DRATCoreVersion$' = 'Publishes the semantic version of the loaded Core bundle.'
        'ehide$' = 'Closes a compatibility HTML-comment region.'
        'EndCheckRegistry$' = 'Closes a check table when no aggregate footer is wanted.'
        'EndListSection$' = 'Closes a caller-owned reusable list section.'
        'err$' = 'Renders caller-supplied error text.'
        'if$' = 'Renders one of two caller-supplied paragraphs.'
        'legendRight$' = 'Moves a Plotly legend to the right of a figure.'
        'legendTop$' = 'Moves a Plotly legend above a figure.'
        'logX$' = 'Selects a logarithmic Plotly x-axis.'
        'logY$' = 'Selects a logarithmic Plotly y-axis.'
        'ok$' = 'Renders caller-supplied success text.'
        'pagebreak$' = 'Inserts an explicit print page break.'
        'plotDashed$' = 'Adds a dashed line trace to a Plotly figure.'
        'plotMarkers$' = 'Adds a line-and-marker trace to a Plotly figure.'
        'ref$' = 'Renders caller-supplied reference text.'
        'sampleParametric$' = 'Samples caller-supplied parametric functions for plotting.'
        'scatterY2$' = 'Adds a scatter trace on the secondary y-axis.'
        'shide$' = 'Opens a compatibility HTML-comment region.'
        'tab$' = 'Inserts fixed non-breaking horizontal space.'
        'ValidationIsError' = 'Lets worksheets classify one validation status as an error.'
        'vline$' = 'Adds a vertical reference line to a Plotly figure.'
        'xBand$' = 'Adds a vertical shaded band to a Plotly figure.'
        'xRange$' = 'Sets an explicit Plotly x-axis range.'
        'y2Range$' = 'Sets an explicit secondary Plotly y-axis range.'
        'yRange$' = 'Sets an explicit Plotly y-axis range.'
    }
}
