alter table scan_run drop key `UK__prep_id_rescan_number`;
alter table scan_run drop column rescan_number;
drop view if exists sections;


CREATE VIEW `sections` AS
select
	`sc`.`id` AS `id`,
	`a`.`prep_id` AS `prep_id`,
	`s`.`file_name` AS `czi_file`,
	`s`.`slide_physical_id` AS `slide_physical_id`,
	`s`.`id` AS `FK_slide_id`,
	`sc`.`file_name` AS `file_name`,
	`sc`.`id` AS `tif_id`,
	`sc`.`scene_number` AS `scene_number`,
	`sc`.`scene_index` AS `scene_index`,
	`sc`.`channel` AS `channel`,
	`sc`.`channel` - 1 AS `channel_index`,
	`sc`.`active` AS `active`,
	`sc`.`created` AS `created`
from
	(((`animal` `a`
join `scan_run` `sr` on
	(`a`.`prep_id` = `sr`.`FK_prep_id`))
join `slide` `s` on
	(`sr`.`id` = `s`.`FK_scan_run_id`))
join `slide_czi_to_tif` `sc` on
	(`s`.`id` = `sc`.`FK_slide_id`))
where
	`s`.`slide_status` = 'Good'
	and `sc`.`active` = 1;