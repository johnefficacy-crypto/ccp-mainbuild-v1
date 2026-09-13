# OPT-LOAD-04_questions.ps1
#
# Loads optional PYQ questions into pyq_questions, one subject-paper at a time.
#
# BLOCKED until OPT-FRONTLOAD-02 ships: the v2 importer rejects
# question_type='descriptive'. Run the dry run now to validate the mapping;
# -Execute will fail until the importer accepts descriptive rows.
#
#   .\OPT-LOAD-04_questions.ps1 -CorpusDir .\workbench\corpus\optionals -Subject psir -Paper 1
#   .\OPT-LOAD-04_questions.ps1 -CorpusDir .\workbench\corpus\optionals -Subject psir -Paper 1 -Execute
#
# ── Numbering (M3) ───────────────────────────────────────────────────────
# pyq_questions.question_number is an INTEGER, but the corpus carries "1a".
# Mapping is positional and deterministic:
#
#     question_number = display_order = block_start + (corpus display_order - 1)
#
# display_order is already 1..N in corpus order within a subject-paper, so the
# block is filled densely from its start. Both columns take the same value
# because pyq_questions_paper_display_order_uidx and
# pyq_questions_paper_question_number_uidx are BOTH per-paper unique, and all
# twelve subject-papers for a year share ONE paper row.
#
# Max observed rows in a subject-paper is 43 (History Paper-1, Q1 expands to
# 20 map items) against a block of 50. A block overflow is a hard stop.
#
# The human-readable "1a" is preserved in source_question_ref (M4) and in
# metadata.corpus_question_number, so nothing is lost by the integer mapping.

[CmdletBinding()]
param(
    [Parameter(Mandatory)][string] $CorpusDir,
    [Parameter(Mandatory)][ValidateSet('psir','pubad','sociology','anthropology','history','geography')]
    [string] $Subject,
    [Parameter(Mandatory)][ValidateSet(1,2)][int] $Paper,
    [string] $PaperLedger   = "workbench\ledgers\OPT-LOAD-02_optional_year_papers.csv",
    [string] $SubjectLedger = "workbench\ledgers\OPT-LOAD-03_subjects_sections.csv",
    [switch] $Execute
)

$ErrorActionPreference = 'Stop'

# corpus file stem and the optional_subject string it carries
$map = @{
    psir         = @{ file='upsc-psir-pyq.json';  name='Political Science and International Relations'; ref='PSIR' }
    pubad        = @{ file='upsc-pubad-pyq.json'; name='Public Administration';                        ref='PUBAD' }
    sociology    = @{ file='upsc-socio-pyq.json'; name='Sociology';                                    ref='SOCIO' }
    anthropology = @{ file='upsc-anth-pyq.json';  name='Anthropology';                                 ref='ANTH' }
    history      = @{ file='upsc-hist-pyq.json';  name='History';                                      ref='HIST' }
    geography    = @{ file='upsc-geog-pyq.json';  name='Geography';                                    ref='GEOG' }
}
$m = $map[$Subject]

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
                $script:hdr = New-Hdr; continue
            }
            throw (Get-ErrBody $_)
        }
    }
}

# ── Ledgers: the only record of paper_id / section_id / block ────────────
if (-not (Test-Path $PaperLedger))   { throw "paper ledger not found: $PaperLedger" }
if (-not (Test-Path $SubjectLedger)) { throw "subject ledger not found: $SubjectLedger" }

$paperById = @{}
Import-Csv $PaperLedger | ForEach-Object { $paperById[[int]$_.year] = $_.paper_id }

$slug = "upsc-cse-mains-opt-$Subject-p$Paper"
$sub  = Import-Csv $SubjectLedger | Where-Object { $_.slug -eq $slug }
if (-not $sub) { throw "no ledger row for $slug" }
$blockStart = [int]$sub.block_start
$sectionId  = $sub.section_id

Write-Host "$($m.name) Paper-$Paper" -ForegroundColor Cyan
Write-Host "  subject_id $($sub.subject_id)"
Write-Host "  section_id $sectionId"
Write-Host "  block      $blockStart-$($blockStart+49)"

# ── Corpus ───────────────────────────────────────────────────────────────
$corpus = Get-Content -Raw -Encoding UTF8 (Join-Path $CorpusDir $m.file) | ConvertFrom-Json
$papers = @($corpus.papers | Where-Object { $_.paper_number -eq $Paper })
Write-Host "  years      $($papers.Count)"

# ── Build every row, validating as we go ─────────────────────────────────
$rows = @(); $problems = @(); $skipped = @()
foreach ($p in $papers) {
    $y = [int]$p.exam_cycle_year
    $paperId = $paperById[$y]
    if (-not $paperId) { $problems += "no optional year-paper for $y"; continue }

    $n = 0
    foreach ($q in $p.questions) {
        $n++
        $num = $blockStart + $n - 1
        if ($num -ge $blockStart + 50) {
            $problems += "$y overflows its 50-slot block at $($q.question_number)"
            break
        }
        $meta = @{
            corpus_question_number = $q.question_number
            parent_question_number = $q.parent_question_number
            section_ref            = $q.section_ref
            is_compulsory          = $q.is_compulsory
            marks_source           = $q.marks_source
            extraction_source      = $(if ($p.source_document_id) { $p.source_document_id }
                                        elseif ($p.source_url)     { $p.source_url }
                                        else { $corpus.extraction_meta.source_file })
            verified_against_official = $false
            paper_kind             = 'optional'
            optional_subject       = $m.name
            optional_paper_number  = $Paper
        }
        if ($null -ne $q.marks)          { $meta['marks']           = $q.marks }
        if ($null -ne $q.marks_inferred) { $meta['marks_inferred']  = $q.marks_inferred }
        # A map item carries only UPSC's locational hint; the place name is the
        # answer and lives on the map sheet, which no compilation reproduces.
        # It is therefore unattemptable from the corpus alone, and the paper asks
        # for a short note per item, not the 150 words a Q1 sub-part would take.
        if ($q.map_item) {
            $meta['map_item']           = $true
            $meta['question_format']    = 'map_identification_item'
            $meta['requires_map_sheet'] = $true
            $meta['answerable_from_text_alone'] = $false
            $meta['note'] = 'Locational hint only. The map sheet UPSC supplies is not reproduced in any compilation, so this item cannot be attempted from the text.'
        }
        elseif ($null -ne $q.word_limit) { $meta['word_limit'] = $q.word_limit }
        if ($q.structure_anomaly)        { $meta['structure_anomaly']   = $q.structure_anomaly }

        # A row flagged duplicate_in_source is byte-identical to another row in
        # the same paper. pyq_questions_paper_hash_uidx is unique on
        # (pyq_paper_id, normalized_question_hash), so the second insert cannot
        # land - it surfaces as a 500 because the question insert is unwrapped.
        # The duplication is the compiler's error (Sociology 2014 Paper-2 prints
        # Q5 and Q6 with identical (b) and (c)); the real text is unknown, so
        # inventing a distinguishing snippet would fabricate a UPSC question.
        # Skip it, record it, and resolve against the official paper later.
        if ($q.duplicate_in_source) {
            $skipped += [pscustomobject]@{
                year = $y; corpus_question_number = $q.question_number
                reason = 'duplicate_in_source - identical text already in this paper'
                text_head = $q.question_text.Substring(0, [Math]::Min(60, $q.question_text.Length))
            }
            continue
        }

        $rows += [pscustomobject]@{
            year            = $y
            pyq_paper_id    = $paperId
            section_id      = $sectionId
            question_number = $num
            display_order   = $num
            source_ref      = "$($m.ref)-P$Paper-$($p.exam_cycle_year)-$($q.question_number)"
            idempotency_key = "opt:${slug}:${y}:$($q.question_number)"
            question_text   = $(if ($q.map_item) {
                                    # UPSC prints the item label, and two items can
                                    # share a hint ("Mesolithic site" at (ii) and (ix)).
                                    # pyq_questions_paper_hash_uidx is unique on
                                    # (pyq_paper_id, normalized_question_hash), so the
                                    # bare hint collides. The label is in the source.
                                    $lbl = $q.question_number -replace '^\d+', ''
                                    "$lbl $($q.question_text)".Trim()
                                } else { $q.question_text })
            metadata        = $meta
        }
    }
}

Write-Host "`n  rows built $($rows.Count)"
$rows | Group-Object year | Sort-Object Name |
    Select-Object @{n='year';e={$_.Name}}, @{n='rows';e={$_.Count}},
                  @{n='range';e={ "$(($_.Group.question_number|Measure-Object -Min).Minimum)-$(($_.Group.question_number|Measure-Object -Max).Maximum)" }} |
    Format-Table -AutoSize

# uniqueness holds per paper, and all subjects share a year's paper row
$dupe = $rows | Group-Object pyq_paper_id, question_number | Where-Object Count -gt 1
if ($dupe) { $problems += "duplicate (paper, question_number) on $($dupe.Count) key(s)" }
$empty = $rows | Where-Object { -not $_.question_text.Trim() }
if ($empty) { $problems += "$($empty.Count) empty question_text" }

if ($problems) {
    Write-Host "`nPROBLEMS - not safe to load:" -ForegroundColor Red
    $problems | ForEach-Object { Write-Host "  - $_" }
    return
}
Write-Host "  validation clean" -ForegroundColor Green
if ($skipped.Count) {
    Write-Host "`n  SKIPPED $($skipped.Count) row(s) flagged duplicate_in_source:" -ForegroundColor Yellow
    $skipped | Format-Table -AutoSize
    Write-Host "  These cannot be inserted - the paper already holds identical text." -ForegroundColor Yellow
    Write-Host "  Resolve against the official paper, then load them separately." -ForegroundColor Yellow
}

if (-not $Execute) {
    Write-Host "`nDRY RUN - nothing written." -ForegroundColor Yellow
    Write-Host "Sample payload:" -ForegroundColor Cyan
    $s = $rows[0]
    @{ reason = "optionals frontload - $($m.name) Paper-$Paper $($s.year)"
       payload = @{
           pyq_paper_id        = $s.pyq_paper_id
           section_id          = $s.section_id
           question_number     = $s.question_number
           display_order       = $s.display_order
           source_question_ref = $s.source_ref
           idempotency_key     = $s.idempotency_key
           question_text       = $s.question_text
           question_type       = 'descriptive'
           metadata            = $s.metadata
       }} | ConvertTo-Json -Depth 8 | Write-Host
    Write-Host "`nNOTE: -Execute will fail until OPT-FRONTLOAD-02 ships." -ForegroundColor Yellow
    return
}

# ── Load ─────────────────────────────────────────────────────────────────
# uq_pyq_questions_idempotency_key makes a re-post of the same row safe, so an
# interrupted run resumes by simply running again.
# The CMS question route is a plain INSERT: uq_pyq_questions_idempotency_key
# stops a duplicate row, but the conflict surfaces as an unhandled 500. So a
# re-run must skip what is already loaded rather than re-post it.
Write-Host "`nChecking what this subject-paper already holds..." -ForegroundColor Cyan
$already = @{}
foreach ($ppid in ($rows.pyq_paper_id | Select-Object -Unique)) {
    $off = 0
    do {
        $pg = Invoke-Cms GET "$cms/pyq-questions?pyq_paper_id=$ppid&limit=200&offset=$off"
        foreach ($e in $pg.items) { if ($e.source_question_ref) { $already[$e.source_question_ref] = $true } }
        $off += 200
    } while ($pg.items.Count -eq 200)
}
$before = $rows.Count
$rows = @($rows | Where-Object { -not $already.ContainsKey($_.source_ref) })
Write-Host "  already loaded $($before - $rows.Count), to load $($rows.Count)"
if (-not $rows) { Write-Host "Nothing to do." -ForegroundColor Green; return }

$done = 0; $ledger = @(); $failed = @()
foreach ($r in $rows) {
    $body = @{
        reason  = "optionals frontload - $($m.name) Paper-$Paper $($r.year)"
        payload = @{
            pyq_paper_id        = $r.pyq_paper_id
            section_id          = $r.section_id
            question_number     = $r.question_number
            display_order       = $r.display_order
            source_question_ref = $r.source_ref
            idempotency_key     = $r.idempotency_key
            question_text       = $r.question_text
            question_type       = 'descriptive'
            metadata            = $r.metadata
        }
    } | ConvertTo-Json -Depth 8

    try {
        $resp = Invoke-Cms POST "$cms/pyq-questions" $body
        $done++
        $ledger += [pscustomobject]@{
            question_id = $resp.row.id; year = $r.year
            question_number = $r.question_number; source_ref = $r.source_ref
        }
        if ($done % 25 -eq 0) { Write-Host "  $done / $($rows.Count)" }
    } catch {
        Write-Host "  FAILED at $($r.source_ref): $_" -ForegroundColor Red
        $failed += $r.source_ref
        if ($failed.Count -ge 20) { Write-Host "  20 failures - stopping." -ForegroundColor Red; break }
    }
    Start-Sleep -Milliseconds 120
}

Write-Host "`nloaded $done / $($rows.Count)" -ForegroundColor Green
if ($skipped.Count) {
    $sp = "workbench\ledgers\OPT-LOAD-04_${Subject}_p${Paper}_SKIPPED.csv"
    New-Item -ItemType Directory -Force -Path (Split-Path $sp) | Out-Null
    $skipped | Export-Csv -NoTypeInformation -Encoding UTF8 (Join-Path (Get-Location) $sp)
    Write-Host "Skipped rows recorded: $sp" -ForegroundColor Yellow
}
$path = "workbench\ledgers\OPT-LOAD-04_${Subject}_p${Paper}.csv"
New-Item -ItemType Directory -Force -Path (Split-Path $path) | Out-Null
$ledger | Export-Csv -NoTypeInformation -Encoding UTF8 (Join-Path (Get-Location) $path)
Write-Host "Ledger: $path" -ForegroundColor Cyan
Write-Host "Questions land reviewer_status=pending. Review is a separate gate; tagging is another." -ForegroundColor Yellow
