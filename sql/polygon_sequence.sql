SELECT AS2.id, AS2.FK_prep_id, AU.id, AU.username , group_concat(AL.label) , AS2.annotation
FROM annotation_session AS2 
INNER JOIN annotation_label AL 
INNER JOIN annotation_session_labels ASL ON (AS2.id = ASL.annotationsession_id AND AL.id = ASL.annotationlabel_id)
inner join auth_user AU ON AS2.FK_user_id = AU.id
WHERE 1=1 
-- and asl.annotationlabel_id in (16)
and AS2.FK_user_id=1
-- and AL.label_type = 'cell'
-- and AL.label like 'Round3_Unsure_2000'
-- and ASL.annotationlabel_id in (24,97)
-- and AS2.annotation like '%volume%'
-- and AL.label like '%C%'
and AS2.FK_prep_id = 'DK41'
and AS2.active = 1
group by AS2.id
ORDER BY AS2.FK_prep_id, AL.label; 


delete from annotation_session_labels where annotationsession_id > 8091;
delete from annotation_session where id > 8091;

select * from annotation_session as2
inner join auth_user au on as2.FK_user_id = au.id
inner join annotation_l
where FK_prep_id = 'DK78'
and active = 1;

insert into annotation_label (label_type, label) values ('cell', 'Fiducialjunk');

select * from annotation_label al
where label like 'Fiducial'
order by al.label;

select distinct as2.id, as2.created, as2.updated 
from annotation_session as2 
inner join marked_cells mc on as2.id = mc.FK_session_id
inner join annotation_label al on mc.source = al.label 
where as2.active = 1
and as2.id in (4059, 4060)
order by as2.id; 

SELECT annotation_session.id,
ASL.annotationlabel_id,
	`annotation_session`.`active`,
	`annotation_session`.`created`,
	`annotation_session`.`id`,
	`annotation_session`.`FK_prep_id`,
	`annotation_session`.`FK_user_id`,
	`annotation_session`.`annotation`,
	`annotation_session`.`updated`
FROM
	`annotation_session`
INNER JOIN `annotation_session_labels` ASL ON
	(`annotation_session`.`id` = ASL.`annotationsession_id`)
WHERE
	(`annotation_session`.`active` = True
		AND ASL.`annotationlabel_id` IN (97, 24)
			AND `annotation_session`.`FK_prep_id` = 'DK41'
			AND `annotation_session`.`FK_user_id` = 38)
group by annotation_session.id
ORDER BY
	`annotation_session`.`created` DESC;

SELECT
annotation_session.id,
	`annotation_session`.`active`,
	`annotation_session`.`created`,
	`annotation_session`.`id`,
	`annotation_session`.`FK_prep_id`,
	`annotation_session`.`FK_user_id`,
	`annotation_session`.`annotation`,
	`annotation_session`.`updated`
FROM
	`annotation_session`
INNER JOIN `annotation_session_labels` ON
	(`annotation_session`.`id` = `annotation_session_labels`.`annotationsession_id`)
INNER JOIN `annotation_session_labels` T4 ON
	(`annotation_session`.`id` = T4.`annotationsession_id`)
WHERE
	(`annotation_session`.`active` = True
		AND `annotation_session_labels`.`annotationlabel_id` = 97
		AND T4.`annotationlabel_id` = 24
		AND `annotation_session`.`FK_prep_id` = 'DK41'
		AND `annotation_session`.`FK_user_id` = 38)
ORDER BY
	`annotation_session`.`created` DESC;



select as2.id, ASL.*, al.*
from annotation_session as2
inner join annotation_session_labels ASL on as2.id = ASL.annotationsession_id
inner join annotation_label al on ASL.annotationlabel_id = al.id
where as2.id = 4059;

desc annotation_session;

select *
from annotation_session as2 
inner join auth_user au on as2.FK_user_id = au.id
inner join annotation_label al on as2.FK_label_id ;


select label, length(label)
from annotation_label where label in ('IC','SC');

select * 
from annotation_session_labels;