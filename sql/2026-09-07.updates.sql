ALTER TABLE annotation_session ADD COLUMN FK_updated_by_id int(11) after FK_user_id;
UPDATE annotation_session 
SET FK_updated_by_id = FK_user_id 
where TO_DAYS(created) != TO_DAYS(updated) and HOUR(created) = HOUR(updated);

DROP TABLE IF EXISTS neuroglancer_log;
CREATE TABLE `neuroglancer_log` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `FK_user_id` int(11) NOT NULL,
  `FK_state_id` int(11) NOT NULL,
  `created` datetime(6) NOT NULL,
  `note` longtext NOT NULL,
  PRIMARY KEY (`id`),
  KEY `K__FK_user_id` (`FK_user_id`),
  KEY `K__FK_state_id` (`FK_state_id`),
  CONSTRAINT `FK__auth_user_FK_user_id` FOREIGN KEY (`FK_user_id`) REFERENCES `auth_user` (`id`),
  CONSTRAINT `FK__neuroglancer_state_FK_state_id` FOREIGN KEY (`FK_state_id`) REFERENCES `neuroglancer_state` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;


select distinct FK_updated_by_id from annotation_session;

desc neuroglancer_state;

select count(*) from neuroglancer_state where FK_prep_id is not null;