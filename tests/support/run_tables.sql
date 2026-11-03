-- The four AI run tables, copied from PortHub contracts/db/schema.sql at e118093 (CT-17), with their
-- CHECK constraints and generated columns. Foreign keys are removed: their tables aren't created here.
-- Also two trimmed tables the failed path writes: terminal_recommendations and baplie_files.

CREATE TABLE `part1_runs` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `berthing_request_id` bigint unsigned NOT NULL,
  `status` enum('QUEUED','RUNNING','DONE','FAILED','REPLACED') NOT NULL DEFAULT 'QUEUED',
  `outcome` enum('WINDOWS_FOUND','NO_FEASIBLE_WINDOW','ENV_DATA_UNAVAILABLE') DEFAULT NULL,
  `retry_count` tinyint NOT NULL DEFAULT '0' COMMENT '0..3',
  `entry_window_proposal_id` bigint unsigned DEFAULT NULL COMMENT 'Set only when windows are found',
  `queued_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `started_at` datetime DEFAULT NULL,
  `finished_at` datetime DEFAULT NULL,
  `result_handled_at` datetime DEFAULT NULL COMMENT 'Set by the Backend when it has handled the C-06 result (Backend only)',
  PRIMARY KEY (`id`),
  KEY `fk_p1r_request` (`berthing_request_id`),
  KEY `fk_p1r_proposal` (`entry_window_proposal_id`),
  CONSTRAINT `chk_p1r_retry` CHECK ((`retry_count` between 0 and 3))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `solver_runs` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `trigger_type` enum('NEW_REQUEST','REPLAN','RESOURCE_CHANGE','MANUAL') NOT NULL,
  `triggered_by` bigint unsigned DEFAULT NULL,
  `horizon_start` datetime NOT NULL,
  `horizon_end` datetime NOT NULL,
  `status` enum('QUEUED','RUNNING','OPTIMAL','FEASIBLE','INFEASIBLE','ERROR') NOT NULL DEFAULT 'QUEUED',
  `objective_value` decimal(14,4) DEFAULT NULL,
  `solve_time_ms` int DEFAULT NULL,
  `solver_version` varchar(40) NOT NULL,
  `result_detail` json DEFAULT NULL COMMENT 'INFEASIBLE: binding constraints; ERROR: error message',
  `queued_at` datetime NOT NULL,
  `started_at` datetime DEFAULT NULL,
  `finished_at` datetime DEFAULT NULL,
  `result_handled_at` datetime DEFAULT NULL COMMENT 'Set by the Backend when it has handled the C-06 result (Backend only)',
  PRIMARY KEY (`id`),
  KEY `fk_sr_user` (`triggered_by`),
  CONSTRAINT `chk_sr_finished` CHECK (((`status` in (_utf8mb4'QUEUED',_utf8mb4'RUNNING')) or (`finished_at` is not null))),
  CONSTRAINT `chk_sr_horizon` CHECK ((`horizon_end` > `horizon_start`)),
  CONSTRAINT `chk_sr_manual` CHECK (((`trigger_type` <> _utf8mb4'MANUAL') or (`triggered_by` is not null))),
  CONSTRAINT `chk_sr_time` CHECK (((`solve_time_ms` is null) or (`solve_time_ms` >= 0)))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='Port-wide joint solve (FR-1.4.1). INFEASIBLE is final; FIFO fallback only on technical failure (recommendation.source = FIFO).';

CREATE TABLE `yard_runs` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `terminal_recommendation_id` bigint unsigned NOT NULL,
  `triggered_by` bigint unsigned DEFAULT NULL,
  `status` enum('QUEUED','RUNNING','DONE','FAILED','REPLACED') NOT NULL DEFAULT 'QUEUED',
  `outcome` enum('YARD_REC_GENERATED','GENERATION_FAILED') DEFAULT NULL,
  `error_category` enum('INVALID_ENVELOPE','PRECONDITION_FAILED','DATA_UNAVAILABLE','CONFIGURATION_ERROR','INFEASIBLE','TIMEOUT','INTERNAL_ERROR') DEFAULT NULL,
  `retry_count` tinyint NOT NULL DEFAULT '0',
  `result_detail` json DEFAULT NULL,
  `worker_version` varchar(40) DEFAULT NULL,
  `queued_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `started_at` datetime DEFAULT NULL,
  `finished_at` datetime DEFAULT NULL,
  `active_key` bigint unsigned GENERATED ALWAYS AS (if((`status` in (_utf8mb4'QUEUED',_utf8mb4'RUNNING')),`terminal_recommendation_id`,NULL)) STORED,
  `result_handled_at` datetime DEFAULT NULL COMMENT 'Set by the Backend when it has handled the C-06 result (Backend only)',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_yr_active` (`active_key`),
  KEY `idx_yr_tr` (`terminal_recommendation_id`),
  KEY `fk_yr_user` (`triggered_by`),
  CONSTRAINT `chk_yr_error` CHECK (((`status` = _utf8mb4'FAILED') = (`error_category` is not null))),
  CONSTRAINT `chk_yr_finished` CHECK (((`status` in (_utf8mb4'QUEUED',_utf8mb4'RUNNING',_utf8mb4'REPLACED')) or (`finished_at` is not null))),
  CONSTRAINT `chk_yr_outcome` CHECK ((((`status` = _utf8mb4'DONE') and (`outcome` = _utf8mb4'YARD_REC_GENERATED')) or ((`status` = _utf8mb4'FAILED') and (`outcome` = _utf8mb4'GENERATION_FAILED')) or ((`status` in (_utf8mb4'QUEUED',_utf8mb4'RUNNING',_utf8mb4'REPLACED')) and (`outcome` is null))))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `baplie_parse_runs` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `baplie_file_id` bigint unsigned NOT NULL,
  `source` enum('FILE','STAGED_PAYLOAD') NOT NULL DEFAULT 'FILE',
  `triggered_by` bigint unsigned DEFAULT NULL,
  `status` enum('QUEUED','RUNNING','DONE','FAILED','REPLACED') NOT NULL DEFAULT 'QUEUED',
  `outcome` enum('PARSED','QUARANTINED','REJECTED') DEFAULT NULL,
  `error_category` enum('INVALID_ENVELOPE','PRECONDITION_FAILED','DATA_UNAVAILABLE','CONFIGURATION_ERROR','TIMEOUT','INTERNAL_ERROR') DEFAULT NULL,
  `retry_count` tinyint NOT NULL DEFAULT '0',
  `container_count` int DEFAULT NULL,
  `result_detail` json DEFAULT NULL,
  `worker_version` varchar(40) DEFAULT NULL,
  `queued_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `started_at` datetime DEFAULT NULL,
  `finished_at` datetime DEFAULT NULL,
  `active_key` bigint unsigned GENERATED ALWAYS AS (if((`status` in (_utf8mb4'QUEUED',_utf8mb4'RUNNING')),`baplie_file_id`,NULL)) STORED,
  `result_handled_at` datetime DEFAULT NULL COMMENT 'Set by the Backend when it has handled the C-06 result (Backend only)',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_bpr_active` (`active_key`),
  KEY `idx_bpr_file` (`baplie_file_id`),
  KEY `fk_bpr_user` (`triggered_by`),
  CONSTRAINT `chk_bpr_error` CHECK (((`status` = _utf8mb4'FAILED') = (`error_category` is not null))),
  CONSTRAINT `chk_bpr_finished` CHECK (((`status` in (_utf8mb4'QUEUED',_utf8mb4'RUNNING',_utf8mb4'REPLACED')) or (`finished_at` is not null))),
  CONSTRAINT `chk_bpr_outcome` CHECK ((((`status` = _utf8mb4'DONE') and (`outcome` is not null)) or ((`status` <> _utf8mb4'DONE') and (`outcome` is null))))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `terminal_recommendations` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `rec_type` enum('TIMING','YARD_PLACEMENT','STORAGE_ALLOCATION') NOT NULL,
  `lifecycle_status` enum('YARD_REC_REQUESTED','YARD_REC_GENERATED','GENERATION_FAILED','YARD_REC_ACCEPTED','YARD_REC_REJECTED','EXPORTED_TO_TOS') DEFAULT NULL,
  `failure_reason` varchar(500) DEFAULT NULL,
  `confidence` decimal(4,3) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `baplie_files` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `parse_status` enum('PENDING','PARSED','FAILED','QUARANTINED') NOT NULL DEFAULT 'PENDING',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
