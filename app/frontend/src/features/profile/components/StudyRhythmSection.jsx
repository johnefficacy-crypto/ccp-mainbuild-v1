import React from "react";
import { useFormContext } from "react-hook-form";
import { InputField, SelectField } from "../../../shared/ui/core";
import { PREPARATION_MODE_OPTIONS } from "../../../lib/profileFields";
import { Grid, Section } from "./shared";
import useExamOptions from "../../../shared/hooks/useExamOptions";

export default function StudyRhythmSection() {
  const { register, formState: { errors, touchedFields } } = useFormContext();
  const err = (k) => touchedFields[k] ? errors[k]?.message : undefined;
  const examOptions = useExamOptions();
  return (
    <Section title="Study rhythm" helper="Used for plan pacing and backlog signals.">
      <Grid>
        <SelectField label="Preparation mode" {...register("study_mode")}>
          <option value="">Not provided</option>
          {PREPARATION_MODE_OPTIONS.map((v) => <option key={v} value={v}>{v.replaceAll("_", " ")}</option>)}
        </SelectField>
        <InputField label="Weekly hours goal" {...register("weekly_hours_goal")} error={err("weekly_hours_goal")} />
        <SelectField label="Target exam" {...register("target_exam")}>
          <option value="">Not provided</option>
          {examOptions.map((e) => <option key={e.value} value={e.value}>{e.label}</option>)}
        </SelectField>
      </Grid>
    </Section>
  );
}
