-- V5__hr_auto_tables.sql
USE `hr_auto`;

CREATE TABLE `report_config` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `report_name` VARCHAR(100) NOT NULL,
  `report_type` VARCHAR(50) NOT NULL,
  `schedule_cron` VARCHAR(50) DEFAULT NULL,
  `template_uri` VARCHAR(500) DEFAULT NULL,
  `output_format` ENUM('PDF','Excel','HTML') NOT NULL DEFAULT 'PDF',
  `enabled` TINYINT(1) NOT NULL DEFAULT 1,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_type` (`report_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `audit_material` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `audit_id` VARCHAR(20) NOT NULL,
  `material_type` VARCHAR(50) NOT NULL,
  `source_module` VARCHAR(50) NOT NULL,
  `file_uri` VARCHAR(500) DEFAULT NULL,
  `generated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `status` ENUM('待生成','生成中','已完成','失败') NOT NULL DEFAULT '待生成',
  PRIMARY KEY (`id`),
  KEY `idx_audit_id` (`audit_id`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `data_insight` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `insight_type` VARCHAR(50) NOT NULL,
  `department` VARCHAR(100) DEFAULT NULL,
  `time_range_start` DATE NOT NULL,
  `time_range_end` DATE NOT NULL,
  `data_snapshot` JSON NOT NULL,
  `ai_analysis` TEXT DEFAULT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_type` (`insight_type`),
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
