-- Carga inicial de ejemplo para canales comerciales.
-- Objetivo:
-- Agrupar clientes / PDVs manualmente segun la logica comercial del cliente,
-- aunque no compartan empresa madre o partner comercial principal.
--
-- Base esperada:
-- - Tabla maestra: zrn_commercial_commercial_channel
-- - Tabla detalle: zrn_commercial_commercial_channel_partner
-- - Regla: un partner solo puede pertenecer a un canal

insert into zrn_commercial_commercial_channel_partner
    (channel_id, partner_id, company_id, sequence, active, create_uid, create_date, write_uid, write_date, notes)
select channel.id,
       partner.id,
       channel.company_id,
       10,
       true,
       2,
       now(),
       2,
       now(),
       'Carga inicial automatica por coincidencia de nombre.'
from zrn_commercial_commercial_channel channel
join res_partner partner on partner.id in (19, 20, 21)
left join zrn_commercial_commercial_channel_partner link on link.partner_id = partner.id
where channel.code = 'la_torre'
  and link.id is null;

insert into zrn_commercial_commercial_channel_partner
    (channel_id, partner_id, company_id, sequence, active, create_uid, create_date, write_uid, write_date, notes)
select channel.id,
       partner.id,
       channel.company_id,
       10,
       true,
       2,
       now(),
       2,
       now(),
       'Carga inicial automatica por coincidencia de nombre.'
from zrn_commercial_commercial_channel channel
join res_partner partner on partner.id in (16, 17)
left join zrn_commercial_commercial_channel_partner link on link.partner_id = partner.id
where channel.code = 'walmart_paiz'
  and link.id is null;

insert into zrn_commercial_commercial_channel_partner
    (channel_id, partner_id, company_id, sequence, active, create_uid, create_date, write_uid, write_date, notes)
select channel.id,
       partner.id,
       channel.company_id,
       10,
       true,
       2,
       now(),
       2,
       now(),
       'Carga inicial automatica por coincidencia de nombre.'
from zrn_commercial_commercial_channel channel
join res_partner partner on partner.id in (18, 28)
left join zrn_commercial_commercial_channel_partner link on link.partner_id = partner.id
where channel.code = 'gta_msf'
  and link.id is null;

insert into zrn_commercial_commercial_channel_partner
    (channel_id, partner_id, company_id, sequence, active, create_uid, create_date, write_uid, write_date, notes)
select channel.id,
       partner.id,
       channel.company_id,
       10,
       true,
       2,
       now(),
       2,
       now(),
       'Carga inicial automatica por coincidencia de nombre.'
from zrn_commercial_commercial_channel channel
join res_partner partner on partner.id in (8)
left join zrn_commercial_commercial_channel_partner link on link.partner_id = partner.id
where channel.code = 'otros'
  and link.id is null;
