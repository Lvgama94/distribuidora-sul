/*
  01 - Banco e schemas
  stg = cópia fiel dos arquivos de data/tratado/ (área de pouso)
  dw  = modelo estrela consumido pelo Power BI
*/
IF DB_ID('DistribuidoraSul') IS NULL
    CREATE DATABASE DistribuidoraSul;
GO
USE DistribuidoraSul;
GO
IF SCHEMA_ID('stg') IS NULL EXEC('CREATE SCHEMA stg');
GO
IF SCHEMA_ID('dw') IS NULL EXEC('CREATE SCHEMA dw');
GO
