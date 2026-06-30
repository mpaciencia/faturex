-- Adicionar coluna user_id à tabela faturas, vinculada à tabela nativa de utilizadores auth.users
ALTER TABLE faturas ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;

-- Ativar Row Level Security (RLS) na tabela faturas
ALTER TABLE faturas ENABLE ROW LEVEL SECURITY;

-- Remover políticas existentes se houver (para evitar duplicados em execuções repetidas)
DROP POLICY IF EXISTS "Utilizadores podem ver apenas as suas próprias faturas" ON faturas;
DROP POLICY IF EXISTS "Utilizadores podem inserir apenas as suas próprias faturas" ON faturas;
DROP POLICY IF EXISTS "Utilizadores podem atualizar apenas as suas próprias faturas" ON faturas;
DROP POLICY IF EXISTS "Utilizadores podem eliminar apenas as suas próprias faturas" ON faturas;

-- Criar políticas de segurança RLS
CREATE POLICY "Utilizadores podem ver apenas as suas próprias faturas" 
ON faturas FOR SELECT 
USING (auth.uid() = user_id);

CREATE POLICY "Utilizadores podem inserir apenas as suas próprias faturas" 
ON faturas FOR INSERT 
WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Utilizadores podem atualizar apenas as suas próprias faturas" 
ON faturas FOR UPDATE 
USING (auth.uid() = user_id);

CREATE POLICY "Utilizadores podem eliminar apenas as suas próprias faturas" 
ON faturas FOR DELETE 
USING (auth.uid() = user_id);
