export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export type Database = {
  // Allows to automatically instantiate createClient with right options
  // instead of createClient<Database, { PostgrestVersion: 'XX' }>(URL, KEY)
  __InternalSupabase: {
    PostgrestVersion: "13.0.4"
  }
  public: {
    Tables: {
      agent_changelog: {
        Row: {
          agent_id: string
          changes: string
          created_at: string
          id: string
          version: string
        }
        Insert: {
          agent_id: string
          changes: string
          created_at?: string
          id?: string
          version: string
        }
        Update: {
          agent_id?: string
          changes?: string
          created_at?: string
          id?: string
          version?: string
        }
        Relationships: [
          {
            foreignKeyName: "agent_changelog_agent_id_fkey"
            columns: ["agent_id"]
            isOneToOne: false
            referencedRelation: "agent_profiles"
            referencedColumns: ["id"]
          },
        ]
      }
      agent_comments: {
        Row: {
          agent_id: string
          comment_type: string | null
          content: string
          created_at: string
          id: string
          parent_id: string | null
          updated_at: string
          user_id: string
        }
        Insert: {
          agent_id: string
          comment_type?: string | null
          content: string
          created_at?: string
          id?: string
          parent_id?: string | null
          updated_at?: string
          user_id: string
        }
        Update: {
          agent_id?: string
          comment_type?: string | null
          content?: string
          created_at?: string
          id?: string
          parent_id?: string | null
          updated_at?: string
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "agent_comments_agent_id_fkey"
            columns: ["agent_id"]
            isOneToOne: false
            referencedRelation: "agent_profiles"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "agent_comments_parent_id_fkey"
            columns: ["parent_id"]
            isOneToOne: false
            referencedRelation: "agent_comments"
            referencedColumns: ["id"]
          },
        ]
      }
      agent_profiles: {
        Row: {
          avg_latency: number | null
          avg_rating: number | null
          capabilities: string[] | null
          category: string | null
          created_at: string
          creator_id: string
          description: string | null
          dockerfile_url: string | null
          github_url: string | null
          id: string
          io_schema: Json | null
          license: string | null
          modalities: string[] | null
          model: string | null
          name: string
          protocols: string[] | null
          runtime_dependencies: string[] | null
          status: string | null
          success_rate: number | null
          tags: string[] | null
          total_runs: number | null
          updated_at: string
          upvotes: number | null
          version: string | null
        }
        Insert: {
          avg_latency?: number | null
          avg_rating?: number | null
          capabilities?: string[] | null
          category?: string | null
          created_at?: string
          creator_id: string
          description?: string | null
          dockerfile_url?: string | null
          github_url?: string | null
          id?: string
          io_schema?: Json | null
          license?: string | null
          modalities?: string[] | null
          model?: string | null
          name: string
          protocols?: string[] | null
          runtime_dependencies?: string[] | null
          status?: string | null
          success_rate?: number | null
          tags?: string[] | null
          total_runs?: number | null
          updated_at?: string
          upvotes?: number | null
          version?: string | null
        }
        Update: {
          avg_latency?: number | null
          avg_rating?: number | null
          capabilities?: string[] | null
          category?: string | null
          created_at?: string
          creator_id?: string
          description?: string | null
          dockerfile_url?: string | null
          github_url?: string | null
          id?: string
          io_schema?: Json | null
          license?: string | null
          modalities?: string[] | null
          model?: string | null
          name?: string
          protocols?: string[] | null
          runtime_dependencies?: string[] | null
          status?: string | null
          success_rate?: number | null
          tags?: string[] | null
          total_runs?: number | null
          updated_at?: string
          upvotes?: number | null
          version?: string | null
        }
        Relationships: []
      }
      agent_reviews: {
        Row: {
          agent_id: string
          created_at: string
          id: string
          rating: number | null
          review_text: string | null
          reviewer_id: string
        }
        Insert: {
          agent_id: string
          created_at?: string
          id?: string
          rating?: number | null
          review_text?: string | null
          reviewer_id: string
        }
        Update: {
          agent_id?: string
          created_at?: string
          id?: string
          rating?: number | null
          review_text?: string | null
          reviewer_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "agent_reviews_agent_id_fkey"
            columns: ["agent_id"]
            isOneToOne: false
            referencedRelation: "agent_profiles"
            referencedColumns: ["id"]
          },
        ]
      }
      collaboration_requests: {
        Row: {
          agent_id: string
          created_at: string
          creator_id: string
          id: string
          message: string | null
          requester_id: string
          status: string | null
          updated_at: string
        }
        Insert: {
          agent_id: string
          created_at?: string
          creator_id: string
          id?: string
          message?: string | null
          requester_id: string
          status?: string | null
          updated_at?: string
        }
        Update: {
          agent_id?: string
          created_at?: string
          creator_id?: string
          id?: string
          message?: string | null
          requester_id?: string
          status?: string | null
          updated_at?: string
        }
        Relationships: [
          {
            foreignKeyName: "collaboration_requests_agent_id_fkey"
            columns: ["agent_id"]
            isOneToOne: false
            referencedRelation: "agent_profiles"
            referencedColumns: ["id"]
          },
        ]
      }
      user_profiles: {
        Row: {
          avatar_url: string | null
          bio: string | null
          created_at: string
          display_name: string | null
          github_username: string | null
          id: string
          reputation_score: number | null
          twitter_username: string | null
          updated_at: string
          user_id: string
          website_url: string | null
        }
        Insert: {
          avatar_url?: string | null
          bio?: string | null
          created_at?: string
          display_name?: string | null
          github_username?: string | null
          id?: string
          reputation_score?: number | null
          twitter_username?: string | null
          updated_at?: string
          user_id: string
          website_url?: string | null
        }
        Update: {
          avatar_url?: string | null
          bio?: string | null
          created_at?: string
          display_name?: string | null
          github_username?: string | null
          id?: string
          reputation_score?: number | null
          twitter_username?: string | null
          updated_at?: string
          user_id?: string
          website_url?: string | null
        }
        Relationships: []
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      [_ in never]: never
    }
    Enums: {
      [_ in never]: never
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}

type DatabaseWithoutInternals = Omit<Database, "__InternalSupabase">

type DefaultSchema = DatabaseWithoutInternals[Extract<keyof Database, "public">]

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema["Tables"] &
        DefaultSchema["Views"])
    ? (DefaultSchema["Tables"] &
        DefaultSchema["Views"])[DefaultSchemaTableNameOrOptions] extends {
        Row: infer R
      }
      ? R
      : never
    : never

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Insert: infer I
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Insert: infer I
      }
      ? I
      : never
    : never

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Update: infer U
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Update: infer U
      }
      ? U
      : never
    : never

export type Enums<
  DefaultSchemaEnumNameOrOptions extends
    | keyof DefaultSchema["Enums"]
    | { schema: keyof DatabaseWithoutInternals },
  EnumName extends DefaultSchemaEnumNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"]
    : never = never,
> = DefaultSchemaEnumNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"][EnumName]
  : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema["Enums"]
    ? DefaultSchema["Enums"][DefaultSchemaEnumNameOrOptions]
    : never

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    | keyof DefaultSchema["CompositeTypes"]
    | { schema: keyof DatabaseWithoutInternals },
  CompositeTypeName extends PublicCompositeTypeNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"]
    : never = never,
> = PublicCompositeTypeNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema["CompositeTypes"]
    ? DefaultSchema["CompositeTypes"][PublicCompositeTypeNameOrOptions]
    : never

export const Constants = {
  public: {
    Enums: {},
  },
} as const
