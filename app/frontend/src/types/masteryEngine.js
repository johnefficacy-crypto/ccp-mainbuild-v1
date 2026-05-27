/**
 * Shared types for the mastery engine (PR5a) output shapes.
 *
 * Single source of truth: app/backend/app/study_os/mastery_engine/schemas.py.
 * The field-for-field contract lives in ./masteryEngine.schema.json; the runtime
 * PropTypes below are derived from it, so they cannot drift from the contract.
 * A pytest drift test (test_schema_frontend_parity.py) fails CI if the contract
 * diverges from schemas.py. See docs/contracts.md.
 *
 * Wire-format note: Pydantic serializes Decimal and UUID to JSON strings, so those
 * fields validate as PropTypes.string here.
 */
import PropTypes from "prop-types";

import contract from "./masteryEngine.schema.json";

const MODELS = contract.models;

const SCALAR_VALIDATORS = {
  str: PropTypes.string,
  int: PropTypes.number,
  float: PropTypes.number,
  bool: PropTypes.bool,
  Decimal: PropTypes.string,
  UUID: PropTypes.string,
};

const shapeConfigCache = {};

function shapeConfigForModel(modelName) {
  if (shapeConfigCache[modelName]) return shapeConfigCache[modelName];
  const config = {};
  // Register before recursing so cross-references resolve against the live object.
  shapeConfigCache[modelName] = config;
  const fields = MODELS[modelName] || {};
  Object.entries(fields).forEach(([fieldName, spec]) => {
    let validator = validatorForToken(spec.type);
    if (spec.required) validator = validator.isRequired;
    config[fieldName] = validator;
  });
  return config;
}

function validatorForToken(token) {
  if (token.startsWith("list[")) {
    const inner = token.slice("list[".length, -1);
    return PropTypes.arrayOf(validatorForToken(inner));
  }
  if (SCALAR_VALIDATORS[token]) return SCALAR_VALIDATORS[token];
  if (MODELS[token]) return PropTypes.shape(shapeConfigForModel(token));
  return PropTypes.any;
}

function modelValidator(modelName) {
  return PropTypes.shape(shapeConfigForModel(modelName));
}

export const AttemptQuestionAnalytics = modelValidator("AttemptQuestionAnalytics");
export const AttemptTopicAnalytics = modelValidator("AttemptTopicAnalytics");
export const CorrectionEvidence = modelValidator("CorrectionEvidence");
export const CorrectionTaskDraft = modelValidator("CorrectionTaskDraft");
export const DerivationResult = modelValidator("DerivationResult");
export const DerivedAttemptAnalytics = modelValidator("DerivedAttemptAnalytics");
export const ErrorPatternSignal = modelValidator("ErrorPatternSignal");
export const MasteryDelta = modelValidator("MasteryDelta");

export const masteryEngineContract = contract;
