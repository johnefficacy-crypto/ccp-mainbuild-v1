BEGIN;

UPDATE public.topics t SET name = v.name, slug = v.slug
FROM (VALUES
  ('2071ecc9-3042-45cc-b6d5-0a2c7970f1c8'::uuid, 'Recent developments: atmospheric & coastal phenomena', 'gs1-recent-developments-atmospheric-coastal-phenomena-a7524f52'),
  ('d0cbe1a6-487b-489a-829a-d2ea63b2a77d'::uuid, 'Recent developments: connectivity & port-led development', 'gs1-recent-developments-connectivity-port-led-development-4228a58f'),
  ('a2940973-ef25-4c58-9165-041c3bc4fa12'::uuid, 'Recent developments: demographic structure & population dynamics', 'gs1-recent-developments-demographic-structure-population-dynamics-f431aa0c'),
  ('bcda1789-d071-48bf-a8ee-e82702b4bdae'::uuid, 'Recent developments: development & welfare indicators', 'gs1-recent-developments-development-welfare-indicators-b0df6fae'),
  ('97de0712-a47f-4f64-95fd-aae8066a0cd0'::uuid, 'Recent developments: himalayan geomorphology & hazards', 'gs1-recent-developments-himalayan-geomorphology-hazards-93e1c63d'),
  ('e639b66e-27b5-4f64-a8bd-63b99acff2e5'::uuid, 'Recent developments: human development & regional disparity', 'gs1-recent-developments-human-development-regional-disparity-6fce266b'),
  ('57ede7d8-7731-408d-8cbf-9d6bb0162930'::uuid, 'Recent developments: labour & livelihood security', 'gs1-recent-developments-labour-livelihood-security-3d94c216'),
  ('7eb21f06-3f74-401b-9246-571fb2e63d07'::uuid, 'Recent developments: marginalised & vulnerable-group welfare', 'gs1-recent-developments-marginalised-vulnerable-group-welfare-02877d86'),
  ('f9271b6e-5473-4f13-a825-414b1e7381cf'::uuid, 'Recent developments: monsoon, climate & extreme-weather geography', 'gs1-recent-developments-monsoon-climate-extreme-weather-geography-23ebce18'),
  ('b31c1e99-dbfd-4941-9290-7d3c41a86ee6'::uuid, 'Recent developments: ocean & climate-system dynamics', 'gs1-recent-developments-ocean-climate-system-dynamics-47452f32'),
  ('3cd771d3-9640-46ca-92ef-8c8122a5d18b'::uuid, 'Recent developments: ocean & seabed mineral geography', 'gs1-recent-developments-ocean-seabed-mineral-geography-a5991dba'),
  ('612af828-a8fa-41fb-8b98-deed0f04b758'::uuid, 'Recent developments: resource & energy geography', 'gs1-recent-developments-resource-energy-geography-f1c20340'),
  ('d2d2fda1-58c9-4693-becc-f9d1aa3e9420'::uuid, 'Recent developments: river-basin & water-resource management', 'gs1-recent-developments-river-basin-water-resource-management-1e1d96e0'),
  ('409dc207-cf36-423c-85a2-a2c4346b4731'::uuid, 'Recent developments: settlement geography & disaster vulnerability', 'gs1-recent-developments-settlement-geography-disaster-vulnerability-2b1e4763'),
  ('83695bd8-b076-41fe-beae-ac618525f864'::uuid, 'Recent developments: social risk & institutional conditions', 'gs1-recent-developments-social-risk-institutional-conditions-0266cf6c'),
  ('dff19fcc-e7e8-4f00-91c8-d46168152f94'::uuid, 'Recent developments: volcanism & tectonic phenomena', 'gs1-recent-developments-volcanism-tectonic-phenomena-56ec3e84'),
  ('c84a04cf-d06b-44cf-a39b-2d1d233835da'::uuid, 'Recent developments: connectivity, security & new-frontier diplomacy', 'gs2-recent-developments-connectivity-security-new-frontier-diplomacy-d93e0e74'),
  ('b44a1adf-7f6e-4bf6-829b-4c25b6ab9cc5'::uuid, 'Recent developments: delivery mechanisms & sectoral missions', 'gs2-recent-developments-delivery-mechanisms-sectoral-missions-0419e2b9'),
  ('f0eca3c5-d9c3-4667-b9ee-05f9b2b4333e'::uuid, 'Recent developments: digital governance & information regimes', 'gs2-recent-developments-digital-governance-information-regimes-85746da5'),
  ('77b22ac6-87d4-4d8b-a8f9-2d35cbc80206'::uuid, 'Recent developments: digital-economy & platform regulation', 'gs2-recent-developments-digital-economy-platform-regulation-57dc4d76'),
  ('8741ea6c-6ddd-4cf5-8ea2-931a4915b1ea'::uuid, 'Recent developments: electoral & political-process reform', 'gs2-recent-developments-electoral-political-process-reform-08a5ca31'),
  ('4c1a049f-93d8-44e1-ad99-ea91ebbd6fce'::uuid, 'Recent developments: federalism, reservation & constitutional status', 'gs2-recent-developments-federalism-reservation-constitutional-status-6a18794d'),
  ('7fe26c02-6058-4722-96df-1d695713e41d'::uuid, 'Recent developments: global governance & multilateral institutions', 'gs2-recent-developments-global-governance-multilateral-institutions-60f43732'),
  ('dcd328bc-5dab-41b3-887d-74e4b6e878fa'::uuid, 'Recent developments: governance indices & accountability', 'gs2-recent-developments-governance-indices-accountability-78d747d9'),
  ('2872c823-a067-4f07-98a6-2cafca7bc16c'::uuid, 'Recent developments: governance, infrastructure & consumer welfare', 'gs2-recent-developments-governance-infrastructure-consumer-welfare-51b4b01d'),
  ('c7fe32a5-b647-47a2-bfd6-b35571412589'::uuid, 'Recent developments: health & nutrition welfare', 'gs2-recent-developments-health-nutrition-welfare-b0774a48'),
  ('eb9512da-20be-4f9a-ba53-22b93a6f176d'::uuid, 'Recent developments: india''s neighbourhood & regional diplomacy', 'gs2-recent-developments-india-s-neighbourhood-regional-diplomacy-01e56044'),
  ('83499214-66c6-447c-81dc-24f619b81279'::uuid, 'Recent developments: judiciary, rights & rule of law', 'gs2-recent-developments-judiciary-rights-rule-of-law-d215f05a'),
  ('ef75955e-b8c2-4243-929e-22d91c8568f7'::uuid, 'Recent developments: marginalised-community & rights-based welfare', 'gs2-recent-developments-marginalised-community-rights-based-welfare-c6da0fda'),
  ('086fcfd4-93cf-4440-967d-5af19b5cdad4'::uuid, 'Recent developments: strategic partnerships & major-power relations', 'gs2-recent-developments-strategic-partnerships-major-power-relations-e0ff8ba2'),
  ('9ce1866d-2cc2-47d6-bb43-1ae9cc09c24b'::uuid, 'Recent developments: AI, digital technology & recognition', 'gs3-recent-developments-ai-digital-technology-recognition-a5ee6cbf'),
  ('50f567a0-1935-4a77-be6f-edbc18a9800f'::uuid, 'Recent developments: agriculture & resource economics', 'gs3-recent-developments-agriculture-resource-economics-27f24db2'),
  ('f2ae88fa-34ec-4090-ab2e-81ad921e95f1'::uuid, 'Recent developments: air pollution & control regimes', 'gs3-recent-developments-air-pollution-control-regimes-3aafabdd'),
  ('8d27db6a-20ce-444a-b49d-234ca301a5e3'::uuid, 'Recent developments: biotechnology & medical science', 'gs3-recent-developments-biotechnology-medical-science-3aa13a27'),
  ('b91fb326-e3f0-4e78-a2fa-33cbe5ed4a6c'::uuid, 'Recent developments: border & territorial security', 'gs3-recent-developments-border-territorial-security-3344e564'),
  ('135082bc-d1b2-46fd-b73b-99a2ce1eb321'::uuid, 'Recent developments: case studies & sector-specific disaster risk', 'gs3-recent-developments-case-studies-sector-specific-disaster-risk-24b7f74e'),
  ('d594130c-6968-4204-a72c-1813a5c423a0'::uuid, 'Recent developments: climate mitigation & industrial transition', 'gs3-recent-developments-climate-mitigation-industrial-transition-0bceefb1'),
  ('deb8d50c-856e-4569-9e26-111749b4a24a'::uuid, 'Recent developments: cyber & information security', 'gs3-recent-developments-cyber-information-security-fb0ec403'),
  ('01e8ce53-5baa-4562-becf-6b729e965ab5'::uuid, 'Recent developments: defence preparedness & terror financing', 'gs3-recent-developments-defence-preparedness-terror-financing-213d1a4e'),
  ('246b3d92-845d-4cce-ac10-ccecb0d4da7d'::uuid, 'Recent developments: early-warning & technology in disaster management', 'gs3-recent-developments-early-warning-technology-in-disaster-management-a07d4d93'),
  ('f2ce7115-701d-429b-83d3-346aaf9a1b82'::uuid, 'Recent developments: employment & demographic economics', 'gs3-recent-developments-employment-demographic-economics-f029400b'),
  ('e33a0781-b54e-4c13-b139-a2d1be703304'::uuid, 'Recent developments: external sector & global economy', 'gs3-recent-developments-external-sector-global-economy-990c0456'),
  ('747557b5-a1f6-4742-b2a0-fcc7c4e467f3'::uuid, 'Recent developments: forest & land degradation', 'gs3-recent-developments-forest-land-degradation-54b16324'),
  ('168c3918-75a9-4941-8be8-38afce9e706f'::uuid, 'Recent developments: frontier physics & materials science', 'gs3-recent-developments-frontier-physics-materials-science-d824d881'),
  ('ce7c5c58-b604-4317-b3a3-27daa3622074'::uuid, 'Recent developments: industrial & sectoral policy', 'gs3-recent-developments-industrial-sectoral-policy-75d20057'),
  ('2958a963-1280-41ca-9c2f-7fd6b4202b93'::uuid, 'Recent developments: industry, infrastructure & manufacturing economics', 'gs3-recent-developments-industry-infrastructure-manufacturing-economics-3a4f849f'),
  ('4f0a8f23-1e09-4558-901b-30c67e3015b1'::uuid, 'Recent developments: inequality, wages & welfare economics', 'gs3-recent-developments-inequality-wages-welfare-economics-e968b55a'),
  ('57138567-7b38-438c-93d2-23f3a4dff4af'::uuid, 'Recent developments: infrastructure financing & monetisation', 'gs3-recent-developments-infrastructure-financing-monetisation-5c1a6408'),
  ('6df12641-44c4-4eba-9743-651614015436'::uuid, 'Recent developments: institutional & policy frameworks', 'gs3-recent-developments-institutional-policy-frameworks-d123f2aa'),
  ('0228683a-38b5-4b1a-93de-96c424296cc7'::uuid, 'Recent developments: institutions and S&T policy', 'gs3-recent-developments-institutions-and-s-t-policy-e74db96b'),
  ('baae92c1-8cdc-4c91-b529-3da4945c393d'::uuid, 'Recent developments: internal conflict & law-and-order', 'gs3-recent-developments-internal-conflict-law-and-order-f400c9d6'),
  ('76558b71-03c7-4831-a443-e8cc4629059e'::uuid, 'Recent developments: marine & coastal ecosystem degradation', 'gs3-recent-developments-marine-coastal-ecosystem-degradation-82a02a6d'),
  ('5988fe67-d79a-4c02-8588-232fbf3619b9'::uuid, 'Recent developments: maritime & space security', 'gs3-recent-developments-maritime-space-security-2906f995'),
  ('1573b5bf-4244-4c9b-92cb-24b1a844aeba'::uuid, 'Recent developments: monetary & financial-sector policy', 'gs3-recent-developments-monetary-financial-sector-policy-31802bc7'),
  ('5f764b03-ef7f-40e1-9b42-26bc3ef4b01f'::uuid, 'Recent developments: space missions & policy', 'gs3-recent-developments-space-missions-policy-ebfbd50a'),
  ('b760b5e5-7807-4ca6-a920-6070a5761e1f'::uuid, 'Recent developments: species conservation & wildlife management', 'gs3-recent-developments-species-conservation-wildlife-management-ecc104ac'),
  ('4f5f8547-4be1-4a90-8459-0b5cf2bed568'::uuid, 'Recent developments: waste & materials management', 'gs3-recent-developments-waste-materials-management-7c269a4e'),
  ('7a8e7992-b648-4226-8356-8c203e260ca7'::uuid, 'Recent developments: wetlands & water security', 'gs3-recent-developments-wetlands-water-security-04dc9a3f')
) AS v(id, name, slug)
WHERE t.id = v.id;

DO $$
DECLARE n int;
BEGIN
  SELECT count(*) INTO n FROM public.topics WHERE name LIKE 'Recent developments:%';
  IF n <> 58 THEN RAISE EXCEPTION 'expected 58 prefixed rows, got %', n; END IF;
END $$;

COMMIT;
