-- Demo-läge som ett EGET flagga, inte infererat ur data.
--
-- Tidigare avgjordes "demo" av att workspacen HADE data (workspaceHasData),
-- men det kan inte skilja en marknadsföringsdemo med påhittad data från en
-- kund som faktiskt matat in sitt eget bolag — och det kan inte heller styra
-- ett löptak. En demo-workspace är en egen instans UTAN förladdad data som
-- får testa mot sitt eget bolag med begränsat antal körningar.

alter table public.workspaces
  add column if not exists is_demo boolean not null default false;
