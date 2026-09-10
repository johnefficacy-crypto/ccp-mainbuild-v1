# OPT-LOAD-02_optional_year_papers.ps1
#
# Creates ONE optional pyq_papers row per year (M1/B2), not one per subject.
# Six subjects share each year's paper; sections separate them.
#
# Questions are NOT loaded here — the v2 importer still rejects
# question_type='descriptive' (OPT-FRONTLOAD-02).
#
# DRY RUN BY DEFAULT. Nothing is written without -Execute.
#
#   .\OPT-LOAD-02_optional_year_papers.ps1 -CorpusDir .\corpus
#   .\OPT-LOAD-02_optional_year_papers.ps1 -CorpusDir .\corpus -SourceId <uuid> -Execute
#
# pyq_papers has NO unique constraint and NO idempotency key, so every create is
# guarded by a pre-flight check on metadata.paper_code. (pyq_questions DOES have
# uq_pyq_questions_idempotency_key — that is why the question loader will differ.)

[CmdletBinding()]
param(
    [Parameter(Mandatory)][string] $CorpusDir,
    [string] $SourceId,
    [switch] $Execute
)

$ErrorActionPreference = 'Stop'

$examId  = '5466e62f-7382-4a38-ba96-2fe5fbfeaba2'
$phaseId = '626ec667-4bbf-4420-8715-48c5b83e0d11'   # Mains template phase, cycle null

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
                $script:hdr = New-Hdr        # rebuild: the old hashtable holds the dead token
                continue
            }
            throw (Get-ErrBody $_)
        }
    }
}

# ── Wake ─────────────────────────────────────────────────────────────────
Write-Host "Waking service..." -ForegroundColor Cyan
for ($i = 1; $i -le 10; $i++) {
    $c = curl.exe -s -o NUL -w "%{http_code}" "$cms/pyq-papers?limit=1" `
         -H "Authorization: Bearer $env:CCP_ADMIN_JWT"
    if ($c -eq '200') { break }
    if ($c -eq '401') { throw "401 - refresh CCP_ADMIN_JWT and re-run" }
    Write-Host "  $i : $c"; Start-Sleep -Seconds 15
}
if ($c -ne '200') { throw "service did not wake" }

# ── Read every subject corpus, group by year ─────────────────────────────
$files = Get-ChildItem -Path $CorpusDir -Filter 'upsc-*-pyq.json' |
         Where-Object { $_.Name -notlike '*topicwise*' -and $_.Name -notlike '*ocr*' }
if (-not $files) { throw "no corpus files found in $CorpusDir" }

$byYear = @{}
foreach ($f in $files) {
    $c = Get-Content -Raw -Encoding UTF8 $f.FullName | ConvertFrom-Json
    foreach ($p in $c.papers) {
        $y = [int]$p.exam_cycle_year
        if (-not $byYear.ContainsKey($y)) { $byYear[$y] = @() }
        $byYear[$y] += [pscustomobject]@{
            subject   = $p.optional_subject
            paper_no  = $p.paper_number
            questions = $p.questions.Count
            src_file  = $c.extraction_meta.source_file
        }
    }
    Write-Host ("  {0,-28} {1,3} papers" -f $f.Name, $c.papers.Count)
}

$years = $byYear.Keys | Sort-Object
Write-Host "`nYears: $($years.Count)  ($($years[0])-$($years[-1]))" -ForegroundColor Cyan
foreach ($y in $years) {
    $g = $byYear[$y]
    Write-Host ("  {0}  subjects {1,2}  papers {2,2}  questions {3,4}" -f `
        $y, ($g.subject | Select-Object -Unique).Count, $g.Count,
        ($g | Measure-Object questions -Sum).Sum)
}

# ── Existing papers on the Mains phase (paged: list routes 422 above 200) ─
$existing = @(); $offset = 0
do {
    $page = Invoke-Cms GET "$cms/pyq-papers?exam_id=$examId&exam_phase_id=$phaseId&limit=200&offset=$offset"
    $existing += $page.items; $offset += 200
} while ($page.items.Count -eq 200)

$seen = @{}
foreach ($p in $existing) { if ($p.metadata.paper_code) { $seen[$p.metadata.paper_code] = $p.id } }
Write-Host "`nExisting Mains papers: $($existing.Count)   (GS year-papers are untouched by this script)"

# ── Plan ─────────────────────────────────────────────────────────────────
$plan = foreach ($y in $years) {
    $g = $byYear[$y]
    [pscustomobject]@{
        year       = $y
        paper_code = "UPSC-CSE-MAINS-OPT-$y"
        subjects   = ($g.subject | Select-Object -Unique).Count
        papers     = $g.Count
        questions  = ($g | Measure-Object questions -Sum).Sum
        exists     = $seen.ContainsKey("UPSC-CSE-MAINS-OPT-$y")
        detail     = $g
    }
}
$toCreate = @($plan | Where-Object { -not $_.exists })

Write-Host "`nPlan: create $($toCreate.Count), skip $(($plan | Where-Object exists).Count)" -ForegroundColor Cyan
$plan | Select-Object year, paper_code, subjects, papers, questions, exists | Format-Table -AutoSize

if (-not $Execute) {
    Write-Host "DRY RUN - nothing written. Re-run with -SourceId <uuid> -Execute." -ForegroundColor Yellow
    if ($toCreate.Count) {
        Write-Host "`nSample payload:" -ForegroundColor Cyan
        $s = $toCreate[0]
        @{ reason = "frontload UPSC CSE Mains optional papers $($s.year)"
           payload = @{
               pyq_source_id = '<SourceId>'
               exam_id       = $examId
               exam_phase_id = $phaseId
               year          = $s.year
               source_type   = 'aggregator'
               metadata      = @{
                   paper_code       = $s.paper_code
                   paper_kind       = 'optional'
                   optional_subjects = @($s.detail | ForEach-Object { "$($_.subject) Paper-$($_.paper_no)" })
                   question_count   = $s.questions
                   verified_against_official = $false
                   promotion_blocked_by = 'no source_document_id - see M5'
               }
           }} | ConvertTo-Json -Depth 8 | Write-Host
    }
    return
}

if (-not $SourceId) { throw "-SourceId is required for -Execute. Create the pyq_source row first." }

# ── Create ───────────────────────────────────────────────────────────────
$ledger = @(); $n = 0
foreach ($s in $toCreate) {
    $n++
    $body = @{
        reason  = "frontload UPSC CSE Mains optional papers $($s.year)"
        payload = @{
            pyq_source_id = $SourceId
            exam_id       = $examId
            exam_phase_id = $phaseId
            year          = $s.year
            source_type   = 'aggregator'
            metadata      = @{
                paper_code        = $s.paper_code
                paper_kind        = 'optional'
                optional_subjects = @($s.detail | ForEach-Object { "$($_.subject) Paper-$($_.paper_no)" })
                question_count    = $s.questions
                verified_against_official = $false
                promotion_blocked_by = 'no source_document_id - see M5'
            }
        }
    } | ConvertTo-Json -Depth 8

    try {
        $r  = Invoke-Cms POST "$cms/pyq-papers" $body
        $id = $r.row.id                          # response is {ok, audit_id, row:{id}}
        Write-Host ("  [{0}/{1}] {2} -> {3}" -f $n, $toCreate.Count, $s.paper_code, $id) -ForegroundColor Green
        $ledger += [pscustomobject]@{
            paper_code = $s.paper_code; paper_id = $id; year = $s.year
            subjects = $s.subjects; questions = $s.questions
            created_at = (Get-Date -Format s)
        }
    } catch {
        Write-Host ("  [{0}/{1}] {2} FAILED: {3}" -f $n, $toCreate.Count, $s.paper_code, $_) -ForegroundColor Red
        Write-Host "  Stopping. Ledger holds everything created so far." -ForegroundColor Yellow
        break
    }
    Start-Sleep -Milliseconds 200
}

# ── Ledger ───────────────────────────────────────────────────────────────
$path = "workbench\ledgers\OPT-LOAD-02_optional_year_papers.csv"
New-Item -ItemType Directory -Force -Path (Split-Path $path) | Out-Null
$full = Join-Path (Get-Location) $path
if (Test-Path $full) { $ledger = @(Import-Csv $full) + $ledger }
$ledger | Export-Csv -NoTypeInformation -Encoding UTF8 $full

Write-Host "`nLedger: $path  ($($ledger.Count) rows)" -ForegroundColor Cyan
Write-Host "Commit it - paper_code -> paper_id is the join key the question load needs." -ForegroundColor Yellow
Write-Host "`nNext: create the 12 subjects and their sections, then OPT-FRONTLOAD-02." -ForegroundColor Cyan