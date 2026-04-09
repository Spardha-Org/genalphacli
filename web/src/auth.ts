import NextAuth from "next-auth";
import GitHub from "next-auth/providers/github";
import { DrizzleAdapter } from "@auth/drizzle-adapter";
import { db } from "@/db";
import { eq } from "drizzle-orm";
import { workspaces, workspaceMembers, projects } from "@/db/schema";

export const { handlers, auth, signIn, signOut } = NextAuth({
  adapter: DrizzleAdapter(db),
  providers: [
    GitHub({
      clientId: process.env.AUTH_GITHUB_ID,
      clientSecret: process.env.AUTH_GITHUB_SECRET,
      authorization: {
        params: {
          scope: "read:user user:email",
        },
      },
    }),
  ],
  session: { strategy: "database" },
  events: {
    async createUser({ user }) {
      // Auto-create workspace + default project on first sign-up
      if (!user.id) return;

      const slug =
        user.name?.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") ||
        `workspace-${user.id.slice(0, 8)}`;

      const [workspace] = await db
        .insert(workspaces)
        .values({
          name: user.name ? `${user.name}'s Workspace` : "My Workspace",
          slug,
          ownerId: user.id,
        })
        .returning();

      await db.insert(workspaceMembers).values({
        workspaceId: workspace.id,
        userId: user.id,
        role: "owner",
      });

      await db.insert(projects).values({
        workspaceId: workspace.id,
        name: "Default Project",
        description: "Your first project — add services by pasting a GitHub URL.",
      });
    },
  },
  callbacks: {
    async session({ session, user }) {
      // Attach workspace info to session
      const membership = await db.query.workspaceMembers.findFirst({
        where: eq(workspaceMembers.userId, user.id),
        with: { workspace: true },
      });

      return {
        ...session,
        user: {
          ...session.user,
          id: user.id,
          workspaceId: membership?.workspace.id,
          workspaceSlug: membership?.workspace.slug,
        },
      };
    },
  },
  pages: {
    signIn: "/",
  },
});
