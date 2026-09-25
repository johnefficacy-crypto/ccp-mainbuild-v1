# Signs pending primary tags whose question is already verified.
# Excludes the 23 questions whose tag is being replaced by SQL.
# Run from D:\GovtExamAgent\ccp-operator
$sweep   = "sweep_rbi2"
$exp     = "review_out_rbi2"
$drafts  = "workbench\audit\rbi_grade_b\drafts"

$qs   = Get-Content "$exp\questions_export.json" -Raw | ConvertFrom-Json
$tags = Get-Content "$exp\tags_export.json" -Raw | ConvertFrom-Json

$qStatus = @{}; foreach ($q in $qs) { $qStatus[$q.id] = $q.reviewer_status }
$tagInfo = @{}; foreach ($t in $tags) { $tagInfo[$t.id] = $t }

$retag = @{}
Import-Csv "$drafts\rbi_domain_review_ALL_judged.csv" |
  Where-Object tag_ok -eq 'no' | ForEach-Object { $retag[$_.question_id] = $true }

$signed = 0; $skipRetag = 0; $skipQ = 0; $files = 0
foreach ($f in Get-ChildItem $sweep -Filter "worksheet-*.csv") {
  $rows = Import-Csv $f.FullName
  $touched = 0
  foreach ($r in $rows) {
    if ($r.row_type -ne 'tag') { continue }
    $t = $tagInfo[$r.row_id]; if (-not $t) { continue }
    if ($t.tag_role -ne 'primary') { continue }
    if ($t.reviewer_status -ne 'pending') { continue }
    if ($retag.ContainsKey($t.question_id)) { $skipRetag++; continue }
    if ($qStatus[$t.question_id] -ne 'verified') { $skipQ++; continue }
    $r.decision = 'verified'; $signed++; $touched++
  }
  if ($touched) { $rows | Export-Csv $f.FullName -NoTypeInformation -Encoding utf8; $files++ }
}
"tags signed              : {0}" -f $signed
"skipped (retag pending)  : {0}" -f $skipRetag
"skipped (question not ok): {0}" -f $skipQ
"worksheets written       : {0}" -f $files
