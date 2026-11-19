DROP TABLE IF EXISTS `cell_data`;

DROP TABLE IF EXISTS `region_of_interest`;
CREATE TABLE `region_of_interest` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `FK_state_id` int(11) NOT NULL,
  `FK_prep_id` varchar(20) NOT NULL,
  `layer_name` varchar(50) NOT NULL,
  `volume_name` varchar(50) NOT NULL,
  `section` INT(11) NOT NULL DEFAULT 0,
  `com_x` DOUBLE NOT NULL DEFAULT 0.00 ,
  `com_y` DOUBLE NOT NULL DEFAULT 0.00 ,
  `area` DOUBLE NOT NULL DEFAULT 0,
  `contour_count` INT(11) NOT NULL DEFAULT 0, 
  `active` tinyint(1) NOT NULL DEFAULT 1,
  `created` datetime(6) NOT NULL DEFAULT current_timestamp(6),
  PRIMARY KEY (`id`),
  UNIQUE KEY `UK__roi_ids` (`FK_state_id`,`layer_name`,`volume_name`,`section`),
  KEY `K__roi_FK_prep_id` (`FK_prep_id`),
  KEY `K__roi_FK_state_id` (`FK_state_id`),
  CONSTRAINT `FK__roi_FK_prep_id` FOREIGN KEY (`FK_prep_id`) REFERENCES `animal` (`prep_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `FK__roi_FK_state_id` FOREIGN KEY (`FK_state_id`) REFERENCES `neuroglancer_state` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;





CREATE TABLE `cell_data` (
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  `FK_roi_id` int(11) NOT NULL COMMENT 'ROI that the data belong to',
  `com_x` DOUBLE NOT NULL DEFAULT 0.00 ,
  `com_y` DOUBLE NOT NULL DEFAULT 0.00 ,
  `area` DOUBLE NOT NULL DEFAULT 0.00 ,
  PRIMARY KEY (`id`),
  KEY `K__region_data_FK_roi_id` (`FK_roi_id`),
  CONSTRAINT `FK__region_data_roi_id` FOREIGN KEY (`FK_roi_id`) REFERENCES `region_of_interest` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;


