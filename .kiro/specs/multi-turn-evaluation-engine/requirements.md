# Multi-Turn Evaluation Engine Requirements

## Introduction

This document outlines the requirements for enhancing the existing evaluation engine to support unified single-turn and multi-turn evaluation capabilities. The goal is to create a comprehensive evaluation orchestration layer that can seamlessly integrate with various benchmark tools and task sources while maintaining compatibility with the existing lm-evaluation-harness framework.

## Requirements

### Requirement 1: Unified Task Type Architecture

**User Story:** As an evaluation engineer, I want to define both single-turn and multi-turn tasks as distinct task type classes within the same evaluation engine, so that I can manage all evaluation scenarios through a unified interface.

#### Acceptance Criteria

1. WHEN the system initializes THEN it SHALL recognize two primary task type classes: SingleTurnTask and MultiTurnTask
2. WHEN a task is registered THEN the system SHALL automatically classify it based on its configuration and execution pattern
3. WHEN loading tasks THEN the system SHALL support seamless switching between single-turn and multi-turn execution modes
4. IF a task type is ambiguous THEN the system SHALL default to single-turn mode and log a warning

### Requirement 2: Multi-Source Task Integration

**User Story:** As a benchmark administrator, I want to integrate tasks from multiple sources including custom definitions, lm-eval native tasks, and external benchmark tools, so that I can create comprehensive evaluation suites.

#### Acceptance Criteria

1. WHEN configuring tasks THEN the system SHALL support three task sources: custom (internal DSL/YAML), lm-eval native, and external benchmarks
2. WHEN loading lm-eval tasks THEN the system SHALL maintain full compatibility with existing HumanEval, MBPP, and APPS tasks
3. WHEN integrating external benchmarks THEN the system SHALL support SWE-bench, InterCode, ConvCodeBench, BugsInPy, Defects4J, and QuixBugs through adapters
4. WHEN a task source is unavailable THEN the system SHALL gracefully handle the error and continue with available tasks

### Requirement 3: Unified Environment Interface

**User Story:** As a task developer, I want to implement tasks using a standardized environment interface with reset(), step(), success(), and info() methods, so that all tasks follow consistent execution patterns regardless of their source.

#### Acceptance Criteria

1. WHEN implementing any task THEN it SHALL conform to the unified Env interface with reset(), step(), success(), and info() methods
2. WHEN a task calls reset() THEN the environment SHALL initialize to a clean starting state and return initial observations
3. WHEN a task calls step(action) THEN the environment SHALL execute the action, update state, and return (observation, reward, done, info)
4. WHEN a task calls success() THEN the environment SHALL return a boolean indicating task completion status
5. WHEN a task calls info() THEN the environment SHALL return metadata about the current state and execution context

### Requirement 4: Comprehensive Metrics System

**User Story:** As a performance analyst, I want to collect detailed metrics across multiple dimensions including task success, efficiency, repair quality, robustness, cost, and safety, so that I can perform thorough evaluation analysis.

#### Acceptance Criteria

1. WHEN an evaluation completes THEN the system SHALL calculate Task Success metrics: Resolved%, Recall, MRR
2. WHEN tracking efficiency THEN the system SHALL measure Avg Turns, Steps, and Redundancy Rate
3. WHEN evaluating repair quality THEN the system SHALL track Edit Churn and Files Touched
4. WHEN assessing robustness THEN the system SHALL calculate Recovery Rate and Stability metrics
5. WHEN monitoring cost THEN the system SHALL record Wall Time per Solved and Token/Cost per Solved
6. WHEN checking safety THEN the system SHALL count Safety Incidents and policy violations

### Requirement 5: Feedback Processing and Safety

**User Story:** As a safety engineer, I want to implement feedback trimming and safety controls to ensure secure and efficient evaluation execution, so that evaluations run within acceptable resource and security boundaries.

#### Acceptance Criteria

1. WHEN processing feedback THEN the system SHALL implement Top-K assertion filtering, stack trace summarization, and file context extraction
2. WHEN feedback exceeds limits THEN the system SHALL apply length truncation while preserving essential information
3. WHEN tools are requested THEN the system SHALL enforce a whitelist of approved tools and commands
4. WHEN resource usage is monitored THEN the system SHALL implement isolation boundaries and usage limits
5. WHEN dangerous commands are detected THEN the system SHALL block execution and log security incidents

### Requirement 6: Standardized Output Format

**User Story:** As a data analyst, I want evaluation results in a consistent CSV/JSON schema format, so that I can easily analyze and compare results across different evaluation runs.

#### Acceptance Criteria

1. WHEN an evaluation completes THEN the system SHALL output results in both CSV and JSON formats
2. WHEN generating output THEN the schema SHALL include: run_id, task_id, sample_id, success, turns, steps, wall_time_s, token_in, token_out, cost_usd, files_touched, edit_added, edit_deleted, redundancy_rate, recovered, safety_incidents, notes
3. WHEN exporting results THEN the system SHALL validate schema compliance before output
4. WHEN results are requested THEN the system SHALL support filtering and aggregation options

### Requirement 7: Multi-Turn Orchestration Engine

**User Story:** As an evaluation orchestrator, I want a dedicated multi-turn orchestration engine that manages turn loops, feedback shaping, termination policies, and safety guards, so that complex multi-turn evaluations execute reliably.

#### Acceptance Criteria

1. WHEN starting multi-turn evaluation THEN the orchestrator SHALL initialize the turn loop with proper state management
2. WHEN processing turns THEN the system SHALL apply feedback shaping rules and context management
3. WHEN evaluating termination THEN the system SHALL check multiple termination conditions: success, max turns, timeout, safety violations
4. WHEN safety violations occur THEN the system SHALL immediately terminate execution and log incidents
5. WHEN turns exceed limits THEN the system SHALL gracefully terminate and record partial results

### Requirement 8: Adapter Architecture

**User Story:** As an integration developer, I want a flexible adapter architecture that allows seamless integration of different benchmark tools and task sources, so that new evaluation frameworks can be easily added.

#### Acceptance Criteria

1. WHEN creating adapters THEN each SHALL implement the unified Env interface
2. WHEN integrating lm-eval THEN the adapter SHALL maintain backward compatibility with existing task configurations
3. WHEN connecting external benchmarks THEN adapters SHALL handle tool-specific initialization, execution, and result parsing
4. WHEN adapter errors occur THEN the system SHALL provide detailed error messages and fallback options
5. WHEN new adapters are added THEN they SHALL be automatically discoverable through the task registry

### Requirement 9: Multiple Interface Support

**User Story:** As a user, I want to access the multi-turn evaluation engine through multiple interfaces including API, CLI, and configuration files, so that I can integrate it into different workflows and automation systems.

#### Acceptance Criteria

1. WHEN using the API THEN all multi-turn evaluation features SHALL be accessible through REST endpoints
2. WHEN using the CLI THEN all functionality SHALL be available through command-line arguments and configuration files
3. WHEN using configuration files THEN the system SHALL support YAML-based task and evaluation definitions
4. WHEN switching interfaces THEN all SHALL provide equivalent functionality and consistent behavior
5. WHEN authentication is required THEN all interfaces SHALL support the same authentication mechanisms

### Requirement 10: Backward Compatibility

**User Story:** As an existing user, I want the enhanced system to maintain full backward compatibility with current evaluation engine functionality, so that my existing workflows continue to work without modification.

#### Acceptance Criteria

1. WHEN upgrading THEN all existing single-turn evaluations SHALL continue to work without changes
2. WHEN using existing APIs THEN all current endpoints SHALL maintain their behavior and response formats
3. WHEN running legacy tasks THEN the system SHALL automatically detect and handle them appropriately
4. WHEN configuration files are used THEN existing YAML configurations SHALL remain valid
5. WHEN errors occur THEN the system SHALL provide clear migration guidance for deprecated features