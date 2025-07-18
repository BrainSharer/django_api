-- updates 2025 07 11
update annotation_session set active=0 where FK_user_id in (1,4,23,41,60);
drop view v_search_sessions;
create view v_search_sessions AS
select
	`AS2`.`id` AS `id`,
	concat(`AS2`.`FK_prep_id`,
	' ',AS2.id,
	' ', group_concat(`AL`.`label` separator ','), 
	' ', `AU`.`username`, 
	' ', json_extract(`AS2`.`annotation`, '$.type')) 
	AS `animal_abbreviation_username`,
	`AL`.`label_type` AS `label_type`,
	date_format(`AS2`.`updated`, '%d %b %Y %H:%i') AS `updated`
from
	(((`annotation_session` `AS2`
join `annotation_label` `AL`)
join `annotation_session_labels` `ASL` on
	(`AS2`.`id` = `ASL`.`annotationsession_id`
		and `AL`.`id` = `ASL`.`annotationlabel_id`))
join `auth_user` `AU` on
	(`AS2`.`FK_user_id` = `AU`.`id`))
where
	`AS2`.`active` = 1
	and `AU`.`is_active` = 1
	and `AL`.`active` = 1
group by
	`AS2`.`id`

