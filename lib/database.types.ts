export type Json = string | number | boolean | null | { [key: string]: Json | undefined } | Json[];

export type Database = {
  public: {
    Tables: {
      workspaces: {
        // slug och ss_tenant_id tillkom i 007_workspace_tenants.sql men saknades
        // här i ett halvår. Följden var inte ett typfel utan tystnad: koden kunde
        // inte läsa kopplingen till supportagentens tenant, så varje kunds
        // dashboard föll tillbaka på demonyckeln utan att någonting klagade.
        Row: {
          id: string;
          name: string;
          locale: string;
          timezone: string;
          products: string[];
          slug: string | null;
          ss_tenant_id: string | null;
          created_at: string;
        };
        Insert: {
          id?: string;
          name: string;
          locale?: string;
          timezone?: string;
          products?: string[];
          slug?: string | null;
          ss_tenant_id?: string | null;
          created_at?: string;
        };
        Update: {
          id?: string;
          name?: string;
          locale?: string;
          timezone?: string;
          products?: string[];
          slug?: string | null;
          ss_tenant_id?: string | null;
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
          updated_at?: string;
        };
        Relationships: [];
      };
      // Finns sedan 006_auth_selfheal.sql men har saknats i den här filen —
      // därför fanns ingen typad skrivväg, och därför blev TeamSettings fyra
      // hårdkodade strängar i stället för riktiga inbjudningar.
      workspace_invites: {
        Row: {
          id: string;
          email: string;
          workspace_id: string;
          role: string;
          invited_by: string | null;
          accepted_at: string | null;
          created_at: string;
        };
        Insert: {
          id?: string;
          email: string;
          workspace_id: string;
          role?: string;
          invited_by?: string | null;
          accepted_at?: string | null;
          created_at?: string;
        };
        Update: {
          id?: string;
          email?: string;
          workspace_id?: string;
          role?: string;
          invited_by?: string | null;
          accepted_at?: string | null;
          created_at?: string;
        };
        Relationships: [];
      };
      // 020_platform_admins.sql. Egen dimension, inte profiles.role — den
      // senare är workspace-scopad och säger inget om plattformsåtkomst.
      platform_admins: {
        Row: {
          user_id: string;
          granted_by: string | null;
          granted_at: string;
        };
        Insert: {
          user_id: string;
          granted_by?: string | null;
          granted_at?: string;
        };
        Update: {
          user_id?: string;
          granted_by?: string | null;
          granted_at?: string;
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