export type Json = string | number | boolean | null | { [key: string]: Json | undefined } | Json[];

export type Database = {
  public: {
    Tables: {
      workspaces: {
        Row: {
          id: string;
          name: string;
          locale: string;
          timezone: string;
          created_at: string;
        };
        Insert: {
          id?: string;
          name: string;
          locale?: string;
          timezone?: string;
          created_at?: string;
        };
        Update: {
          id?: string;
          name?: string;
          locale?: string;
          timezone?: string;
          created_at?: string;
        };
        Relationships: [];
      };
      profiles: {
        Row: {
          id: string;
          workspace_id: string;
          full_name: string;
          role: string;
          created_at: string;
        };
        Insert: {
          id: string;
          workspace_id: string;
          full_name: string;
          role?: string;
          created_at?: string;
        };
        Update: {
          id?: string;
          workspace_id?: string;
          full_name?: string;
          role?: string;
          created_at?: string;
        };
        Relationships: [];
      };
      business_contexts: {
        Row: {
          id: string;
          workspace_id: string;
          product: string;
          target_audience: string;
          industries: string[];
          geography: string[];
          tone: string;
          offer: string;
          cta: string;
          contact_roles: string[];
          company_name: string | null;
          guarantee: string | null;
          terms: string | null;
          delivery: string | null;
          returns_policy: string | null;
          support_email: string | null;
          support_synced_at: string | null;
          updated_at: string;
        };
        Insert: {
          id?: string;
          workspace_id: string;
          product: string;
          target_audience: string;
          industries?: string[];
          geography?: string[];
          tone: string;
          offer: string;
          cta: string;
          contact_roles?: string[];
          company_name?: string | null;
          guarantee?: string | null;
          terms?: string | null;
          delivery?: string | null;
          returns_policy?: string | null;
          support_email?: string | null;
          support_synced_at?: string | null;
          updated_at?: string;
        };
        Update: {
          id?: string;
          workspace_id?: string;
          product?: string;
          target_audience?: string;
          industries?: string[];
          geography?: string[];
          tone?: string;
          offer?: string;
          cta?: string;
          contact_roles?: string[];
          company_name?: string | null;
          guarantee?: string | null;
          terms?: string | null;
          delivery?: string | null;
          returns_policy?: string | null;
          support_email?: string | null;
          support_synced_at?: string | null;
          updated_at?: string;
        };
        Relationships: [];
      };
      // Kopplingen workspace → Snajp-Support-tenant (007_snajp_workspace_link.sql).
      // Läses BARA med service-role-nyckeln; api_key får aldrig nå webbläsaren.
      snajp_workspace_tenants: {
        Row: {
          workspace_id: string;
          tenant_id: string;
          tenant_slug: string | null;
          api_key: string;
          key_prefix: string | null;
          created_at: string;
          updated_at: string;
        };
        Insert: {
          workspace_id: string;
          tenant_id: string;
          tenant_slug?: string | null;
          api_key: string;
          key_prefix?: string | null;
          created_at?: string;
          updated_at?: string;
        };
        Update: {
          workspace_id?: string;
          tenant_id?: string;
          tenant_slug?: string | null;
          api_key?: string;
          key_prefix?: string | null;
          created_at?: string;
          updated_at?: string;
        };
        Relationships: [];
      };
    };
    Views: {
      [_ in never]: never;
    };
    Functions: {
      current_workspace_id: {
        Args: Record<string, never>;
        Returns: string;
      };
    };
    Enums: {
      [_ in never]: never;
    };
    CompositeTypes: {
      [_ in never]: never;
    };
  };
};

export type Workspace = Database["public"]["Tables"]["workspaces"]["Row"];
export type Profile = Database["public"]["Tables"]["profiles"]["Row"];
export type BusinessContext = Database["public"]["Tables"]["business_contexts"]["Row"];
export type BusinessContextInsert = Database["public"]["Tables"]["business_contexts"]["Insert"];