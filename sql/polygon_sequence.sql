SELECT AS2.id, AS2.FK_prep_id, AU.id, AU.username, AS2.updated, group_concat(AL.label) , AS2.annotation
FROM annotation_session AS2 
INNER JOIN annotation_label AL 
INNER JOIN annotation_session_labels ASL ON (AS2.id = ASL.annotationsession_id AND AL.id = ASL.annotationlabel_id)
inner join auth_user AU ON AS2.FK_user_id = AU.id
WHERE 1=1 
-- and asl.annotationlabel_id in (16)
-- and AS2.FK_user_id=1
-- and AL.label_type = 'cell'
-- and AL.label like 'Round3_Unsure_2000'
-- and ASL.annotationlabel_id in (24,97)
-- and AS2.annotation like '%volume%'
-- and AL.label like '%C%'
and AS2.FK_prep_id = 'DKBC006'
and AS2.active = 1
-- and AS2.id = 8094
group by AS2.id
ORDER BY AS2.FK_prep_id, AL.label; 

update annotation_session set annotation = "{}" where id = 8094;


delete from annotation_session_labels where annotationsession_id  in (7395, 8092, 7396, 8093, 7397);
delete from annotation_session where id in (7395, 8092, 7396, 8093, 7397);

desc annotation_session;
desc brain_region;

select * from elastix_transformation et where et.FK_prep_id = 'MD658' order by section;
update elastix_transformation set rotation = 1, xshift=0 where id = 66679;
delete from elastix_transformation where FK_prep_id = 'MD658' and section < 21;