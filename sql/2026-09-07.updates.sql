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

select section,rotation,xshift,yshift from elastix_transformation where FK_prep_id = 'DKSP008' and section > 180 and section < 190;
-- 181	0.00725173	12.5773	0.0329171
-- 182	0.00379232	-10.2936	6.86424
-- 183	-0.0167047	3.3553	35.378
-- 184	0.0116968	-9.21623	-7.45184
-- 185	-0.0000131186	10.5074	-20.5167
-- 186	0.00847611	0.657778	6.47559
-- 187	-0.00670296	-14.1627	17.0361
-- 188	0.0259644	0.430973	-3.95728
-- 189	0.0287928	6.09142	-14.6973
delete from elastix_transformation where FK_prep_id = 'DKSP008' and section > 180 and section < 190;
