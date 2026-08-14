$ErrorActionPreference = 'Stop'

$repositoryRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
. (Join-Path $repositoryRoot 'Tools\PublicApiAuditRules.ps1')

function Assert-AuditRule {
    param(
        [bool]$Condition,
        [string]$Message
    )

    if (-not $Condition) {
        throw $Message
    }
}

$fixture = @(
    '#def Inline$ = ''Inline macros do not create a local scope.',
    'outside_value = 1',
    '#def Example$(value$)',
    '    #hide',
    '    ζTEST_value = value$',
    '    ApprovedRegistry = ζTEST_value',
    '    #for ζTEST_index = 1 : 2',
    '        ζTEST_values.ζTEST_index = ζTEST_value',
    '    #loop',
    '#end def'
)

$assignments = @(Get-CalcPadMacroAssignments -Lines $fixture -Source 'Fixture.cpd')
Assert-AuditRule -Condition ($assignments.Count -eq 3) -Message 'The parser must return direct assignments and iterators only inside multiline macros.'
Assert-AuditRule -Condition ($assignments[0].Name -ceq 'ζTEST_value') -Message 'The parser did not preserve the first local name.'
Assert-AuditRule -Condition ($assignments[1].Name -ceq 'ApprovedRegistry') -Message 'The parser did not preserve an intentional global assignment.'
Assert-AuditRule -Condition ($assignments[2].Kind -ceq 'iterator') -Message 'The parser did not classify the #for iterator.'
Assert-AuditRule -Condition (@($assignments | Where-Object Name -CEQ 'outside_value').Count -eq 0) -Message 'Assignments outside multiline macros must be ignored.'

Assert-AuditRule -Condition (Test-CalcPadMacroLocalName -Name 'ζTEST_value' -Prefix 'TEST') -Message 'A correctly namespaced local must pass.'
Assert-AuditRule -Condition (-not (Test-CalcPadMacroLocalName -Name 'ζOTHER_value' -Prefix 'TEST')) -Message 'A local using another module prefix must fail.'
Assert-AuditRule -Condition (-not (Test-CalcPadMacroLocalName -Name 'ζvalue' -Prefix 'TEST')) -Message 'A zeta local without the module prefix must fail.'
Assert-AuditRule -Condition (-not (Test-CalcPadMacroLocalName -Name 'plain_value' -Prefix 'TEST')) -Message 'An unprefixed local must fail.'

$approval = @{
    Source = 'Fixture.cpd'
    Macros = @('Example$')
    Purpose = 'Fixture registry mutation.'
}
Assert-AuditRule -Condition (Test-CalcPadApprovedGlobalAssignment -Assignment $assignments[1] -Approval $approval) -Message 'An exact approved global assignment must pass.'
$wrongMacroApproval = @{
    Source = 'Fixture.cpd'
    Macros = @('Other$')
    Purpose = 'Invalid fixture registry mutation.'
}
Assert-AuditRule -Condition (-not (Test-CalcPadApprovedGlobalAssignment -Assignment $assignments[1] -Approval $wrongMacroApproval)) -Message 'A global assignment from an unapproved macro must fail.'

Write-Output '[PASS] Public API audit parser and macro namespace rules.'
