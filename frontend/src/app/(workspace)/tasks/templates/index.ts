/**
 * Task Template Registry
 *
 * To add a new template:
 * 1. Create a <template_name>.json file in this directory following the TaskTemplate shape.
 * 2. Import it below and add it to TASK_TEMPLATES.
 */

import { TaskTemplate } from '../tasks.types';

import deepspeedSftDelta from './deepspeed-sft.json';
import vllmInference from './vllm-inference.json';
import sam3Finetune from './sam3-finetune.json';
import sam3Predict from './sam3-predict.json';

export const TASK_TEMPLATES: TaskTemplate[] = [
  deepspeedSftDelta as TaskTemplate,
  vllmInference as TaskTemplate,
  sam3Finetune as TaskTemplate,
  sam3Predict as TaskTemplate
];
