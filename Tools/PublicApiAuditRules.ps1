function Get-CalcPadMacroAssignments {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [AllowEmptyString()]
        [string[]]$Lines,

        [Parameter(Mandatory)]
        [string]$Source
    )

    $assignments = [System.Collections.Generic.List[object]]::new()
    $activeMacro = $null

    for ($lineIndex = 0; $lineIndex -lt $Lines.Count; $lineIndex++) {
        $line = $Lines[$lineIndex]
        if ($null -eq $activeMacro) {
            $macroMatch = [regex]::Match($line, '^\s*#def\s+(?<name>[A-Za-z][A-Za-z0-9_]*\$)(?:\s*\([^)]*\))?\s*$')
            if ($macroMatch.Success) {
                $activeMacro = $macroMatch.Groups['name'].Value
            }
            continue
        }

        if ([regex]::IsMatch($line, '^\s*#end\s+def\s*$')) {
            $activeMacro = $null
            continue
        }

        $assignmentMatch = [regex]::Match($line, '^\s*(?<name>[A-Za-zζ][A-Za-z0-9_ζ]*)\s*=')
        $assignmentKind = 'assignment'
        if (-not $assignmentMatch.Success) {
            $assignmentMatch = [regex]::Match($line, '^\s*#for\s+(?<name>[A-Za-zζ][A-Za-z0-9_ζ]*)\s*=')
            $assignmentKind = 'iterator'
        }
        if (-not $assignmentMatch.Success) {
            continue
        }

        $assignments.Add([pscustomobject]@{
            Name = $assignmentMatch.Groups['name'].Value
            Kind = $assignmentKind
            Macro = $activeMacro
            Source = $Source
            Line = $lineIndex + 1
        })
    }

    return $assignments
}

function Test-CalcPadMacroLocalName {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$Name,

        [Parameter(Mandatory)]
        [string]$Prefix
    )

    $pattern = '^ζ' + [regex]::Escape($Prefix) + '_[A-Za-z][A-Za-z0-9_]*$'
    return [regex]::IsMatch($Name, $pattern)
}

function Test-CalcPadApprovedGlobalAssignment {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [object]$Assignment,

        [Parameter(Mandatory)]
        [System.Collections.IDictionary]$Approval
    )

    $approvedMacros = @($Approval.Macros)
    return $Assignment.Source -ceq [string]$Approval.Source -and $approvedMacros -ccontains $Assignment.Macro
}
