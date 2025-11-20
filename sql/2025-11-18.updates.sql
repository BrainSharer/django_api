DROP VIEW IF EXISTS v_search_sessions;


CREATE VIEW v_search_sessions AS SELECT
	AS2.id AS id,
	CONCAT(AS2.id, ' ', AS2.FK_prep_id, ' ', GROUP_CONCAT(AL.label SEPARATOR ','), ' ', AU.username, ' ', 
	JSON_EXTRACT(AS2.annotation, '$.type')) AS animal_abbreviation_username,
	JSON_EXTRACT(AS2.annotation, '$.type') as label_type,
	DATE_FORMAT(AS2.updated, '%d %b %Y %H:%i') AS updated
FROM annotation_session AS2
INNER JOIN annotation_session_labels ASL ON AS2.id = ASL.annotationsession_id
INNER JOIN annotation_label AL ON ASL.annotationlabel_id = AL.id
INNER JOIN auth_user AU ON AS2.FK_user_id = AU.id
WHERE AS2.active = 1 AND AU.is_active = 1 AND AL.active = 1
GROUP BY AS2.id;
