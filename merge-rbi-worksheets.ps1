# Merges the 412 signed RBI drafts into the sweep worksheets.
# Run from D:\GovtExamAgent\ccp-operator
$drafts = "workbench\audit\rbi_grade_b\drafts"
$sweep  = "sweep_rbi"

$dom = Import-Csv "$drafts\rbi_domain_review_ALL_judged.csv"
$new = Import-Csv "$drafts\rbi_untagged_ALL_tagged.csv"
$tags = Get-Content "review_out_rbi\tags_export.json" -Raw | ConvertFrom-Json

# tag id -> question id
$tagOwner = @{}
foreach ($t in $tags) { $tagOwner[$t.id] = $t.question_id }

# question id -> plan
$plan = @{}
foreach ($r in $dom) {
  $plan[$r.question_id] = [pscustomobject]@{
    difficulty = $r.difficulty
    newtag     = ''                      # retags go via SQL; the worksheet would 409
    verifytag  = ($r.tag_ok -eq 'yes')
    retag      = ($r.tag_ok -eq 'no')
  }
}
foreach ($r in $new) {
  $plan[$r.question_id] = [pscustomobject]@{
    difficulty = $r.difficulty
    newtag     = $r.assign_topic_id      # no existing primary tag, safe to create
    verifytag  = $false
    retag      = $false
  }
}

$q = 0; $tg = 0; $retag = 0; $files = 0
foreach ($f in Get-ChildItem $sweep -Filter "worksheet-*.csv") {
  $rows = Import-Csv $f.FullName
  $touched = 0
  foreach ($r in $rows) {
    if ($r.row_type -eq 'question') {
      $p = $plan[$r.row_id]; if (-not $p) { continue }
      $r.decision   = 'verified'
      $r.difficulty = $p.difficulty
      if ($p.newtag) { $r.assign_topic_id = $p.newtag }
      if ($p.retag)  { $r.notes = 'primary tag replaced by operator SQL after this run'; $retag++ }
      $q++; $touched++
    }
    elseif ($r.row_type -eq 'tag') {
      $qid = $tagOwner[$r.row_id]; if (-not $qid) { continue }
      $p = $plan[$qid]; if (-not $p) { continue }
      if ($p.verifytag) { $r.decision = 'verified'; $tg++; $touched++ }
    }
  }
  if ($touched) { $rows | Export-Csv $f.FullName -NoTypeInformation -Encoding utf8; $files++ }
}
"question rows signed : {0}   (expect 412)" -f $q
"tag rows signed      : {0}   (expect 212)" -f $tg
"retags left for SQL  : {0}   (expect 23)"  -f $retag
"worksheets written   : {0}" -f $files
