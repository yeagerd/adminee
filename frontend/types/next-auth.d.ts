import NextAuth from "next-auth"

declare module "next-auth" {
  interface Session {
    user: {
      id: string
      name?: string | null
      email?: string | null
      image?: string | null
    }
    provider?: string
    providerUserId?: string
    accessToken?: string
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    provider?: string
    providerUserId?: string
    internalUserId?: string
  }
}
