# OPT-LOAD-03_subjects_sections.ps1
#
# Creates the twelve optional subject rows (M2) and one exam_phase_sections row
# each on the Mains template phase (M2b).
#
# DRY RUN BY DEFAULT. Nothing is written without -Execute.
#
#   .\OPT-LOAD-03_subjects_sections.ps1
#   .\OPT-LOAD-03_subjects_sections.ps1 -Execute
#
# subject_group = 'upsc-optional' is DELIBERATELY unmapped in _GROUP_FAMILY.
# family_for_subject() returns None for it, and the caller maps None to the
# generic PYQ-capable policy. That is what these descriptive, PYQ-backed
# subjects want, and it matches the reasoning already recorded for UPSC 'gs':
#   "gs (UPSC General Studies) is intentionally NOT mapped ... those are
#    PYQ-backed subjects and must keep the generic PYQ runtime"
# Do not "fix" this later by mapping it to a family.
#
# The upsc-cse-mains-opt- prefix also keeps every slug clear of _SLUG_FAMILY,
# which contains a bare "maths" -> FAMILY_QUANT entry.

[CmdletBinding()]
param([switch] $Execute)

$ErrorActionPreference = 'Stop'

$phaseId = '626ec667-4bbf-4420-8715-48c5b83e0d11'   # Mains template phase, cycle null
$group   = 'upsc-optional'

if (-not $env:CCP_API_BASE)  { throw "CCP_API_BASE not set" }
if (-not $env:CCP_ADMIN_JWT) { throw "CCP_ADMIN_JWT not set" }
$cms = "$env:CCP_API_BASE/api/admin/exam-intelligence-cms"

function New-Hdr { @{ Authorization = "Bearer $env:CCP_ADMIN_JWT" } }
$hdr = New-Hdr

function Get-ErrBody ($e) {
    try { (New-Object IO.StreamReader($e.Exception.Response.GetResponseStream())).ReadToEnd() }
    catch { $e.Exception.Message }
}

function Invoke-Cms {
    param($Method, $Uri, $Body)
    for ($try = 1; $try -le 2; $try++) {
        try {
            if ($Body) {
                $bytes = [System.Text.Encoding]::UTF8.GetBytes($Body)
                return Invoke-RestMethod -Method $Method -Uri $Uri -Headers $hdr `
                       -Body $bytes -ContentType 'application/json; charset=utf-8'
            }
            return Invoke-RestMethod -Method $Method -Uri $Uri -Headers $hdr
        } catch {
            if ($_.Exception.Response.StatusCode.value__ -eq 401 -and $try -eq 1) {
                Write-Host "  401 - token expired." -ForegroundColor Yellow
                $env:CCP_ADMIN_JWT = Read-Host "  Paste a fresh JWT"
                $script:hdr = New-Hdr
                continue
            }
            throw (Get-ErrBody $_)
        }
    }
}

# ── The twelve. Paper is subject on this exam (M2). ──────────────────────
# Block ranges are M3 and are FIXED - never renumber; a later subject takes 700+.
$defs = @(
  @{ stem='psir';         disp='PSIR';                   p1='Political theory and Indian government and politics'; p2='Comparative politics and international relations'; b1=100; b2=150 }
  @{ stem='pubad';        disp='Public Administration';  p1='Administrative theory';                               p2='Indian administration';                            b1=200; b2=250 }
  @{ stem='sociology';    disp='Sociology';              p1='Fundamentals of sociology';                           p2='Indian society: structure and change';             b1=300; b2=350 }
  @{ stem='anthropology'; disp='Anthropology';           p1='Biological and social anthropology';                  p2='Indian anthropology and tribal issues';            b1=400; b2=450 }
  @{ stem='history';      disp='History';                p1='Ancient and medieval India';                          p2='Modern India and world history';                   b1=500; b2=550 }
  @{ stem='geography';    disp='Geography';              p1='Principles of geography';                             p2='Geography of India';                               b1=600; b2=650 }
)

$plan = foreach ($d in $defs) {
    foreach ($n in 1,2) {
        [pscustomobject]@{
            slug          = "upsc-cse-mains-opt-$($d.stem)-p$n"
            name          = "$($d.disp) Paper-$n (Optional)"
            paper_number  = $n
            syllabus      = if ($n -eq 1) { $d.p1 } else { $d.p2 }
            section_label = "Optional: $($d.disp) Paper-$n"
            block_start   = if ($n -eq 1) { $d.b1 } else { $d.b2 }
        }
    }
}

# ── What already exists ──────────────────────────────────────────────────
$existing = (Invoke-Cms GET "$cms/subjects?q=upsc-cse-mains-opt&limit=200").items
$haveSub = @{}
foreach ($s in $existing) { $haveSub[$s.slug] = $s.id }

$sections = (Invoke-Cms GET "$cms/exam-phase-sections?exam_phase_id=$phaseId&limit=200").items
$haveSec = @{}
foreach ($s in $sections) { $haveSec[$s.section_label] = $s.id }

Write-Host "Existing optional subjects: $($haveSub.Count)"
Write-Host "Existing sections on the Mains phase: $($sections.Count)  (5 = Essay + GS I-IV)"
Write-Host "`nsubject_group = '$group'  -> family_for_subject() returns None -> generic PYQ runtime (intended)" -ForegroundColor Cyan

$plan | Select-Object slug, name, block_start, section_label,
    @{n='subj';e={ if ($haveSub.ContainsKey($_.slug)) {'exists'} else {'create'} }},
    @{n='sect';e={ if ($haveSec.ContainsKey($_.section_label)) {'exists'} else {'create'} }} |
    Format-Table -AutoSize

if (-not $Execute) {
    Write-Host "DRY RUN - nothing written. Re-run with -Execute." -ForegroundColor Yellow
    return
}

# ── Create subjects, then sections ───────────────────────────────────────
$ledger = @()
foreach ($p in $plan) {

    # subject
    $sid = $haveSub[$p.slug]
    if (-not $sid) {
        $body = @{
            reason  = "optionals frontload - subject row for $($p.name)"
            payload = @{
                slug          = $p.slug
                name          = $p.name
                subject_group = $group
                description   = "UPSC CSE Mains optional. Official syllabus: $($p.syllabus)."
                is_active     = $true
                metadata      = @{
                    exam                 = 'upsc-cse'
                    paper_kind           = 'optional'
                    paper_number         = $p.paper_number
                    question_number_block = $p.block_start
                    source               = 'optionals_frontload_rev2'
                }
            }
        } | ConvertTo-Json -Depth 8
        try {
            $sid = (Invoke-Cms POST "$cms/subjects" $body).row.id
            Write-Host "  subject  $($p.slug) -> $sid" -ForegroundColor Green
        } catch {
            Write-Host "  subject  $($p.slug) FAILED: $_" -ForegroundColor Red; break
        }
    } else {
        Write-Host "  subject  $($p.slug) exists -> $sid" -ForegroundColor DarkGray
    }

    # section
    $secId = $haveSec[$p.section_label]
    if (-not $secId) {
        $body = @{
            reason  = "optionals frontload - section for $($p.name)"
            payload = @{
                exam_phase_id = $phaseId
                subject_id    = $sid
                section_label = $p.section_label
                sort_order    = $p.block_start
                metadata      = @{ paper_kind = 'optional'; paper_number = $p.paper_number }
            }
        } | ConvertTo-Json -Depth 8
        try {
            $secId = (Invoke-Cms POST "$cms/exam-phase-sections" $body).row.id
            Write-Host "  section  $($p.section_label) -> $secId" -ForegroundColor Green
        } catch {
            Write-Host "  section  $($p.section_label) FAILED: $_" -ForegroundColor Red; break
        }
    } else {
        Write-Host "  section  $($p.section_label) exists -> $secId" -ForegroundColor DarkGray
    }

    $ledger += [pscustomobject]@{
        slug = $p.slug; subject_id = $sid; section_id = $secId
        section_label = $p.section_label; paper_number = $p.paper_number
        block_start = $p.block_start; created_at = (Get-Date -Format s)
    }
}

# ── Verify sections and subjects agree (M2b) ─────────────────────────────
Write-Host "`nVerifying each section resolves to its own subject..." -ForegroundColor Cyan
$bad = 0
foreach ($r in $ledger) {
    $s = (Invoke-Cms GET "$cms/exam-phase-sections?exam_phase_id=$phaseId&subject_id=$($r.subject_id)&limit=10").items
    $match = $s | Where-Object { $_.id -eq $r.section_id }
    if (-not $match) { Write-Host "  MISMATCH $($r.slug)" -ForegroundColor Red; $bad++ }
}
if ($bad -eq 0) { Write-Host "  all $($ledger.Count) agree" -ForegroundColor Green }

$path = "workbench\ledgers\OPT-LOAD-03_subjects_sections.csv"
New-Item -ItemType Directory -Force -Path (Split-Path $path) | Out-Null
$ledger | Export-Csv -NoTypeInformation -Encoding UTF8 (Join-Path (Get-Location) $path)
Write-Host "`nLedger: $path" -ForegroundColor Cyan
Write-Host "Commit it - subject_id and section_id are what the question load writes against." -ForegroundColor Yellow
Write-Host "`nNext: spike M8 on one PSIR concept row, then OPT-FRONTLOAD-02." -ForegroundColor Cyan
