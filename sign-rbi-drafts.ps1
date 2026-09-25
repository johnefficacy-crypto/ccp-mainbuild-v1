# Signs every RBI draft row as verified. Run from D:\GovtExamAgent\ccp-operator
$dir = "workbench\audit\rbi_grade_b\drafts"
$stamp = "operator bulk-accepted {0}" -f (Get-Date -Format 'yyyy-MM-dd')

foreach ($f in Get-ChildItem $dir -Filter *.csv) {
  $rows = Import-Csv $f.FullName
  foreach ($r in $rows) {
    $r.decision = 'verified'
    if ($r.PSObject.Properties.Name -contains 'proposal_note') {
      $r.proposal_note = (($r.proposal_note, $stamp) -ne '' -join '; ')
    }
  }
  $rows | Export-Csv $f.FullName -NoTypeInformation -Encoding utf8
  "{0}: {1} rows signed" -f $f.Name, $rows.Count
}

$all = Get-ChildItem $dir -Filter *.csv | ForEach-Object { Import-Csv $_.FullName }
"TOTAL signed        : {0}" -f ($all | Where-Object decision -eq 'verified').Count
"with a tag change   : {0}" -f ($all | Where-Object { $_.assign_topic_id }).Count
"blank topic id      : {0}" -f ($all | Where-Object { -not $_.assign_topic_id -and -not $_.current_topic_id }).Count
