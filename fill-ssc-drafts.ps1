# Fills the 39 unmapped rows and re-points para-jumble / sign-interchange rows
# across all 13 SSC CGL draft CSVs, using the leaves added by migration 306.
# Run from D:\GovtExamAgent\ccp-operator

$dir = "workbench\audit\ssc_cgl\drafts"

$NUMSERIES   = 'eec9932e-256a-18d5-0dab-59a425f911a1'   # GIR Number series
$SIGNSWAP    = '01fd4d51-951b-4624-4a21-24ff77be30db'   # GIR Mathematical operations - sign interchange
$VOICE       = '925bca25-49af-bb3b-0e2b-707ca2e0b9fa'   # ENG Active and passive voice
$NARRATION   = 'a628b8f9-5d2f-8502-5517-cc2b1cf0916a'   # ENG Direct and indirect narration
$PARAJUMBLE  = '8d10db27-adf4-21de-1e30-ac69023ab650'   # ENG Sentence rearrangement (para jumble)
$LOGICALORDER= 'b2b889f0-5310-23a4-a50c-daa504f0afe7'   # ENG Logical Order (old parking spot)
$OPMACHINE   = 'dad69132-676d-4a7b-be3d-1da364bd36f9'   # GIR Arithmetic operation machine

$stats = [ordered]@{ numseries=0; voice=0; narration=0; parajumble=0; signswap=0; venn=0 }

foreach ($f in Get-ChildItem $dir -Filter *.csv) {
  $rows = Import-Csv $f.FullName
  foreach ($r in $rows) {

    # 1. unmapped rows -> new leaves
    if ($r.assign_topic_id -eq '') {
      switch -Wildcard ($r.proposed_topic_label) {
        '*number series*'      { $r.assign_topic_id=$NUMSERIES; $r.proposed_topic_label='Number series'; $r.proposal_note="$($r.proposal_note); filled from migration 306"; $stats.numseries++ }
        '*passive*'            { $r.assign_topic_id=$VOICE;     $r.proposed_topic_label='Active and passive voice'; $r.proposal_note="$($r.proposal_note); filled from migration 306"; $stats.voice++ }
        '*narration*'          { $r.assign_topic_id=$NARRATION; $r.proposed_topic_label='Direct and indirect narration'; $r.proposal_note="$($r.proposal_note); filled from migration 306"; $stats.narration++ }
        '*Venn*'               { $stats.venn++ }   # no leaf yet - left blank on purpose
      }
      continue
    }

    # 2. para jumbles off Logical Order onto the dedicated leaf
    if ($r.assign_topic_id -eq $LOGICALORDER) {
      $r.assign_topic_id = $PARAJUMBLE
      $r.proposed_topic_label = 'Sentence rearrangement (para jumble)'
      $r.proposal_note = "$($r.proposal_note); moved off Logical Order per migration 306"
      $stats.parajumble++
      continue
    }

    # 3. sign-interchange rows off the overloaded operation-machine leaf
    if ($r.assign_topic_id -eq $OPMACHINE -and $r.proposal_note -match 'sign interchange') {
      $r.assign_topic_id = $SIGNSWAP
      $r.proposed_topic_label = 'Mathematical operations - sign interchange'
      $r.proposal_note = ($r.proposal_note -replace '; pending sign-interchange leaf','') + '; moved per migration 306'
      $stats.signswap++
    }
  }
  $rows | Export-Csv $f.FullName -NoTypeInformation -Encoding utf8
}

"filled  number series : {0}" -f $stats.numseries
"filled  voice         : {0}" -f $stats.voice
"filled  narration     : {0}" -f $stats.narration
"moved   para jumble   : {0}" -f $stats.parajumble
"moved   sign swap     : {0}" -f $stats.signswap
"still unmapped (Venn) : {0}" -f $stats.venn

$all = Get-ChildItem $dir -Filter *.csv | ForEach-Object { Import-Csv $_.FullName }
"TOTAL rows            : {0}" -f $all.Count
"still blank topic id  : {0}" -f ($all | Where-Object { $_.assign_topic_id -eq '' }).Count
