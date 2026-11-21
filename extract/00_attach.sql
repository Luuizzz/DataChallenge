INSTALL postgres; LOAD postgres;
ATTACH 'service=uhn' AS h (TYPE postgres, READ_ONLY);
