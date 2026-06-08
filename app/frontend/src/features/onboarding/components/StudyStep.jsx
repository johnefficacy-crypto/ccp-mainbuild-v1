import React from "react";
import { useFormContext } from "react-hook-form";
import { InputField, SelectField } from "../../../shared/ui/core";
import { PREPARATION_MODE_OPTIONS } from "../../../lib/profileFields";
import useExamOptions from "../../../shared/hooks/useExamOptions";

export default function StudyStep({ showErrors }) {
  const { register, formState: { errors, touchedFields } } = useFormContext();
  const err = (name) => (showErrors || touchedFields[name]) ? errors[name]?.message : undefined;
  const examOptions = useExamOptions();
  return (
    <div className="grid md:grid-cols-2 gap-4">
      <SelectField label="Preparation mode" {...register("study_mode")}>
        <option value="">Not provided</option>
        {PREPARATION_MODE_OPTIONS.map((p) => <option key={p} value={p}>{p.replaceAll("_", " ")}</option>)}
      </SelectField>
      <InputField label="Weekly hours goal" type="number" {...register("weekly_hours_goal")} error={err("weekly_hours_goal")} />
      <SelectField label="Target exam" {...register("target_exam")}>
        <option value="">Not provided</option>
        {examOptions.map((e) => <option key={e.value} value={e.value}>{e.label}</option>)}
      </SelectField>
    </div>
  );
}
