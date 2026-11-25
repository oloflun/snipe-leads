# Twentys API sett från gränssnittet: reas statiska karta

Skriven 2026-11-25. Underlag för Snajp CRM (licensval A: egen kod). Filen listar NAMNEN på de
GraphQL-operationer Twentys webbklient anropar. Namnen är fakta om ett gränssnitt; ingen kod,
inga frågedokument och inga typer är hämtade ur förlagan.

## Hur kartan togs fram

- Verktyg: `rea-agents` 6.10.1 (morluto/rea, MIT), kört som CLI med en fristående Node 24.22.3
  på D:, utan installationsskript (`npm_config_ignore_scripts=true`) och med taket 1,5 GB heap.
  MCP-servern användes inte: den registrerade 6.7.0 dör på en trasig npx-cache.
- Kommando: `rea analyze-javascript-application <twenty>/packages/twenty-front/src --json`.
  Koden lästes som data och kördes aldrig ("JavaScript syntax was parsed as data and was never
  evaluated" står i resultatet).
- Omfång: 12 957 filer i `twenty-front/src` (commit 1da6d55). Körningen tog cirka 35 minuter och
  gav en resultatfil på 463 MB, som ligger kvar på `D:\snajp-crm-forlaga\rea-run\` utanför repot.
- Utdraget nedan gjordes med ett eget skript som läser filen i block och plockar noder av slaget
  `endpoint`.

## Vad kartan säger

| Slag | Antal unika operationer |
|---|---|
| Frågor | 190 |
| Mutationer | 290 |
| Prenumerationer | 4 |
| Totalt | 484 |

Per område (grupperat på operationens namn, så gränsfall förekommer):

| Område | Frågor | Mutationer | Prenumerationer |
|---|---|---|---|
| Appar, marknadsplats och registrering | 45 | 27 | 0 |
| AI: agenter, chatt, modeller, färdigheter, MCP | 29 | 40 | 1 |
| Arbetsflöden och logikfunktioner | 12 | 29 | 0 |
| Vyer, sidlayout, navigering och kommandomeny | 15 | 30 | 0 |
| Datamodell och metadata | 9 | 15 | 0 |
| Roller, behörigheter och delning | 5 | 13 | 0 |
| Inloggning, sessioner, tvåfaktor och SSO | 10 | 39 | 0 |
| Arbetsyta, medlemmar, domäner och inbjudningar | 21 | 37 | 0 |
| Mejl, kalender, kanaler och utskick | 15 | 23 | 0 |
| Fakturering, krediter och användning | 8 | 16 | 1 |
| Utvecklare: API-nycklar, webhooks, realtid | 4 | 8 | 0 |
| Serveradmin, hälsa, köer och konfiguration | 13 | 10 | 1 |
| Filer, sök, adress, export och berikning | 3 | 3 | 1 |
| Övrigt | 1 | 0 | 0 |

## Begränsningar, ärligt

- **Postoperationerna per objekt syns inte här.** `FindMany<Objekt>`, `FindOne<Objekt>`,
  `Aggregate<Objekt>`, `<Objekt>GroupByRecords`, skapa, uppdatera, radera och slå ihop byggs i
  klienten ur metadata vid körning och har därför inget fast namn i källkoden. De finns i
  genomgången av den körande appen (`twenty-app-kartlaggning.md`, 208 anrop) och i
  källkodsinventeringen (`twenty-07-api-webhooks-appar-mcp.md`).
- **REST syns inte.** Webbklienten talar bara GraphQL. REST-API:t beskrivs ur serverkoden.
- **Den semantiska analysen hann inte allt.** rea avbröt den djupare analysen för de filer som
  kom sist i körningen (resursgräns; 259263 noteringar i resultatet). Den statiska
  läsningen, som ändpunkterna kommer ur, gick igenom alla filer.
- **Rutter:** reas ruttkandidater i den här körningen är egenskapsvägar i testdata (`stage`,
  `amount`), inte sidrutter. Sidrutterna tas ur källkodsinventeringen.
- **Servern gav ingenting användbart.** Samma kommando kördes mot `twenty-server/src/engine/api`
  (682 filer, klar utan fel). rea hittade en enda ändpunktskandidat, och den var ett
  konfigurationsanrop. Verktyget känner igen `fetch` och GraphQL-dokument i klientkod, inte
  NestJS-dekoratorer, så serverns REST-rutter syns inte för det. REST-API:t tas därför ur
  källkodsinventeringen, där en läsare går igenom `engine/api/rest` för hand.

## Operationerna, per område

### Appar, marknadsplats och registrering

**Frågor (45):** `ApplicationConnectedAccounts`, `ApplicationConnectionProviders`, `ApplicationRegistrationTarballUrl`, `CurrentUserApplicationAuthorizations`, `FindAdminApplicationRegistrationClaims`, `FindAdminApplicationRegistrationInstalledWorkspaces`, `FindAdminApplicationRegistrationMonitoring`, `FindAdminApplicationRegistrationStats`, `FindAdminApplicationRegistrationVariables`, `FindAllApplicationRegistrations`, `FindApplicationRegistrationByClientId`, `FindApplicationRegistrationInstallCount`, `FindApplicationRegistrationMonitoring`, `FindApplicationRegistrationStats`, `FindApplicationRegistrationVariables`, `FindClaimableApplicationRegistration`, `FindFrontComponentApplicationCapabilities`, `FindInstallApplicationJobStatus`, `FindManyApplicationRegistrations`, `FindManyApplications`, `FindManyApplicationsForStatus`, `FindManyApplicationsForToolTable`, `FindManyAvailablePackages`, `FindManyFrontComponents`, `FindManyMarketplaceApps`, `FindManyMarketplaceAppsForToolTable`, `FindMarketplaceAppContent`, `FindMarketplaceAppDetail`, `FindMarketplaceAppManifest`, `FindOneAdminApplicationRegistration`, `FindOneApplication`, `FindOneApplicationByUniversalIdentifier`, `FindOneApplicationContent`, `FindOneApplicationName`, `FindOneApplicationRegistration`, `FindOneApplicationSummary`, `FindOneFrontComponent`, `FindUninstallApplicationJobStatus`, `FindUpgradeApplicationJobStatus`, `GetApplicationSdkClientChecksums`, `IsApplicationStopped`, `MyApplicationPreferences`, `WorkflowCodeStepAvailablePackages`, `WorkspaceApplicationAuthorizations`, `WorkspaceApplicationConnectedMemberCounts`

**Mutationer (27):** `ApproveApplicationIframeMediaPermissions`, `authorizeApp`, `ClaimApplicationRegistrationOwnership`, `ConnectApplicationWithApiKey`, `DeleteApplicationRegistration`, `GenerateFrontComponentApplicationTokenPair`, `GrantApplicationCapabilities`, `InstallApplication`, `RenewApplicationToken`, `RevokeApplicationAuthorization`, `RevokeWorkspaceApplicationAuthorization`, `RotateApplicationRegistrationClientSecret`, `RunApplicationHealthCheck`, `RunMyApplicationHealthCheck`, `SyncMarketplaceCatalog`, `TransferApplicationRegistrationOwnership`, `TriggerInstallApplication`, `TriggerUninstallApplication`, `TriggerUpgradeApplication`, `UninstallApplication`, `UpdateAdminApplicationRegistration`, `UpdateAdminApplicationRegistrationVariable`, `UpdateApplication`, `UpdateApplicationRegistration`, `UpdateApplicationRegistrationVariable`, `UpdateMyUserApplicationVariable`, `UpdateOneApplicationVariable`

### AI: agenter, chatt, modeller, färdigheter, MCP

**Frågor (29):** `FindChatMessageAgent`, `FindManyAgents`, `FindManyMcpServers`, `FindManySkills`, `FindManySkillsForSuggestion`, `FindOneAgent`, `FindOneMcpServer`, `FindOneSkill`, `GetAdminAiModels`, `GetAdminAiUsageByWorkspace`, `GetAdminChatThreadMessages`, `GetAdminWorkspaceChatThreads`, `GetAgentChatChannelRoles`, `GetAgentChatChannels`, `GetAgentChatChannelSummaries`, `GetAgentChatChannelThreadIds`, `GetAgentChatOpenThreadsSummary`, `GetAgentRunInsights`, `GetAgentRuns`, `GetAgentRunSummaries`, `GetAiChatUsage`, `GetAiProviders`, `GetAiSystemPromptPreview`, `GetChatMessages`, `GetCustomAiProviderAccess`, `GetModelsDevProviders`, `GetModelsDevSuggestions`, `GetToolIndex`, `GetToolInputSchema`

**Mutationer (40):** `ActivateSkill`, `AddAgentChatMessageReaction`, `AddAgentChatThreadParticipants`, `AddAiProvider`, `AddModelToProvider`, `AnswerToolCall`, `AssignAgentChatThread`, `AssignRoleToAgent`, `CreateAgentChatChannel`, `CreateMcpServer`, `CreateOneAgent`, `CreateSkill`, `DeactivateSkill`, `DeleteAgentChatChannel`, `DeleteMcpServer`, `DeleteOneAgent`, `DeleteQueuedChatMessage`, `DeleteSkill`, `MarkAgentChatThreadAsDoneInChannel`, `MoveAgentChatThreadToChannel`, `RemoveAgentChatMessageReaction`, `RemoveAiProvider`, `RemoveModelFromProvider`, `ReopenAgentChatThreadInChannel`, `RetryChatMessage`, `RunAgent`, `SendChatMessage`, `SetAdminAiModelEnabled`, `SetAdminAiModelsEnabled`, `SetAdminDefaultAiModel`, `SnoozeAgentChatThreadInChannel`, `StartWorkspaceSetupChat`, `StopAgentChatStream`, `SyncMcpServerTools`, `TestMcpToolStep`, `UpdateAgentChatChannel`, `UpdateAgentChatThreadInboxState`, `UpdateMcpServer`, `UpdateOneAgent`, `UpdateSkill`

**Prenumerationer (1):** `OnAgentChatEvent`

### Arbetsflöden och logikfunktioner

**Frågor (12):** `FindManyLogicFunctions`, `FindOneLogicFunction`, `GetCoreWorkflow`, `GetCoreWorkflowLegacyMapping`, `GetCoreWorkflowRunInsights`, `GetCoreWorkflows`, `GetCoreWorkflowsWithCurrentVersions`, `GetCoreWorkflowVersion`, `GetCoreWorkflowVersions`, `GetLogicFunctionSourceCode`, `GettingStartedWorkflowPreviews`, `WorkflowStepConnectedAccountHandle`

**Mutationer (29):** `ActivateCoreWorkflowVersion`, `ComputeStepOutputSchema`, `CreateCoreWorkflow`, `CreateCoreWorkflowVersionEdge`, `CreateCoreWorkflowVersionStep`, `CreateDraftFromCoreWorkflowVersion`, `CreateOneLogicFunction`, `DeactivateCoreWorkflowVersion`, `DeleteCoreWorkflows`, `DeleteCoreWorkflowVersionEdge`, `DeleteCoreWorkflowVersionStep`, `DeleteOneLogicFunction`, `DiscardCoreWorkflowDraft`, `DuplicateCoreWorkflow`, `DuplicateCoreWorkflowVersionStep`, `ExecuteOneLogicFunction`, `PrepareGettingStartedWorkflow`, `RetryWorkflowRun`, `RunCoreWorkflowVersion`, `StopWorkflowRun`, `SubmitFormStep`, `TestHttpRequest`, `TestWorkflowCodeStep`, `UpdateCoreWorkflow`, `UpdateCoreWorkflowVersionPositions`, `UpdateCoreWorkflowVersionStep`, `UpdateCoreWorkflowVersionTrigger`, `UpdateOneLogicFunction`, `UpdateWorkflowRunStep`

### Vyer, sidlayout, navigering och kommandomeny

**Frågor (15):** `BarChartData`, `FindAllRecordFormPageLayouts`, `FindAllRecordPageLayouts`, `FindAllStandalonePageLayouts`, `FindAllViews`, `FindFieldsWidgetViews`, `FindManyCommandMenuItems`, `FindManyNavigationMenuItems`, `FindManyViews`, `FindOnePageLayout`, `FindOnePageLayoutType`, `FindTableWidgetViews`, `GetIframeWidgetMediaPermissions`, `LineChartData`, `PieChartData`

**Mutationer (30):** `CreateManyNavigationMenuItems`, `CreateManyViewFields`, `CreateManyViewGroups`, `CreateView`, `CreateViewFilter`, `CreateViewFilterGroup`, `CreateViewSort`, `DeleteManyNavigationMenuItems`, `DestroyView`, `DestroyViewField`, `DestroyViewFilter`, `DestroyViewFilterGroup`, `DestroyViewSort`, `DuplicateDashboard`, `ResetCommandMenuItem`, `ResetPageLayoutTabToDefault`, `ResetPageLayoutToDefault`, `ResetPageLayoutWidgetToDefault`, `UpdateCommandMenuItem`, `UpdateManyNavigationMenuItems`, `UpdateManyViewGroups`, `UpdatePageLayoutWidget`, `UpdatePageLayoutWithTabsAndWidgets`, `UpdateView`, `UpdateViewField`, `UpdateViewFilter`, `UpdateViewFilterGroup`, `UpdateViewSort`, `UpsertFieldsWidget`, `UpsertViewWidget`

### Datamodell och metadata

**Frågor (9):** `FindManyRelatedRecordPaths`, `FindManyTimelineActivityTypes`, `FindManyValidationRules`, `FindMinimalMetadata`, `FindValidationRulesReadingField`, `MetadataTranslations`, `MostlyEmptyFieldMetadataIds`, `ObjectMetadataItems`, `ObjectRecordCounts`

**Mutationer (15):** `CreateOneFieldMetadataItem`, `CreateOneIndexMetadataItem`, `CreateOneObjectMetadataItem`, `CreateRelatedRecordPath`, `CreateValidationRule`, `DeleteOneFieldMetadataItem`, `DeleteOneIndexMetadataItem`, `DeleteOneObjectMetadataItem`, `DeleteRelatedRecordPath`, `DeleteValidationRule`, `ResetTimelineActivityType`, `UpdateOneFieldMetadataItem`, `UpdateOneObjectMetadataItem`, `UpdateTimelineActivityTypeIsActive`, `UpdateValidationRule`

### Roller, behörigheter och delning

**Frågor (5):** `GetApiKeyRoles`, `GetRecordPermissions`, `GetRecordSharing`, `GetRole`, `GetRoles`

**Mutationer (13):** `AssignRoleToApiKey`, `CreateOneRole`, `DeleteOneRole`, `RemoveRecordShare`, `SetRecordPrivate`, `SetRecordShare`, `UpdateOneRole`, `UpdateWorkspaceIframeMediaPermissions`, `UpdateWorkspaceMemberRole`, `UpsertFieldPermissions`, `UpsertObjectPermissions`, `UpsertPermissionFlags`, `UpsertRowLevelPermissionRules`

### Inloggning, sessioner, tvåfaktor och SSO

**Frågor (10):** `BillingPortalSession`, `CheckUserExists`, `CurrentUserSessions`, `EnterpriseCheckoutSession`, `EnterprisePortalSession`, `GetSigningKeys`, `GetSSOIdentityProviders`, `twoFactorAuthenticationBackupCodeStatus`, `twoFactorAuthenticationRecoveryStatus`, `ValidatePasswordResetToken`

**Mutationer (39):** `CheckoutSession`, `CreateOIDCIdentityProvider`, `CreateSAMLIdentityProvider`, `DeleteSSOIdentityProvider`, `deleteTwoFactorAuthenticationMethod`, `EditSSOIdentityProvider`, `EmailPasswordResetLink`, `GenerateApiKeyToken`, `GeneratePlaygroundToken`, `generateTransientToken`, `generateTwoFactorAuthenticationBackupCodes`, `generateTwoFactorAuthenticationRecoveryCode`, `GenerateTwoFactorAuthenticationRecoveryCodeAsServerAdmin`, `GetAuthorizationUrlForSSO`, `getAuthTokensFromLoginToken`, `getAuthTokensFromOTP`, `getAuthTokensFromSSOExchangeToken`, `getAuthTokensFromTwoFactorAuthenticationRecoveryCode`, `GetLoginTokenFromCredentials`, `Impersonate`, `initiateOTPProvisioning`, `initiateOTPProvisioningForAuthenticatedUser`, `RefreshEnterpriseValidityToken`, `RenewToken`, `ResendEmailVerificationToken`, `RevokeAllOtherUserSessions`, `RevokeSigningKey`, `revokeTwoFactorAuthenticationRecoveryCode`, `RevokeUserSession`, `SignIn`, `SignOut`, `SignUp`, `SignUpInNewWorkspace`, `SignUpInWorkspace`, `StopImpersonation`, `UpdatePasswordViaResetToken`, `VerifyEmailAndGetLoginToken`, `VerifyEmailAndGetWorkspaceAgnosticToken`, `verifyTwoFactorAuthenticationMethodForAuthenticatedUser`

### Arbetsyta, medlemmar, domäner och inbjudningar

**Frågor (21):** `AdminPanelTopWorkspaces`, `CheckWorkspaceSubdomainAvailability`, `FindManyPublicDomains`, `GetApprovedAccessDomains`, `GetCurrentUser`, `GetEmailingDomains`, `GetInstanceAndAllWorkspacesUpgradeStatus`, `GetInviteSuggestions`, `GetOnlineWorkspaceMemberIds`, `GetPublicWorkspaceDataByDomain`, `GetPublicWorkspaceDataById`, `GettingStartedProgress`, `GetWorkspaceAllowedEmbeddingOrigins`, `GetWorkspaceCreationDefaults`, `GetWorkspaceFromInviteHash`, `GetWorkspaceInvitations`, `WorkspaceBillingAdminPanel`, `WorkspaceBillingArrangements`, `WorkspaceDataExports`, `WorkspaceLookupAdminPanel`, `WorkspaceUsageLimits`

**Mutationer (37):** `ActivateWorkspace`, `CheckCustomDomainValidRecords`, `CheckPublicDomainValidRecords`, `CompleteBookCallOnboardingStep`, `CompleteNewWorkspaceLogoUpload`, `CompleteWorkspaceLogoUpload`, `CompleteWorkspaceMemberProfilePictureUpload`, `CreateApprovedAccessDomain`, `CreateNewWorkspaceLogoUpload`, `CreatePublicDomain`, `CreateWorkspaceBillingArrangement`, `CreateWorkspaceDataExport`, `CreateWorkspaceUsageLimit`, `DeleteApprovedAccessDomain`, `DeleteCurrentWorkspace`, `DeletePublicDomain`, `DeleteUserAccount`, `DeleteUserWorkspace`, `DeleteWorkspaceInvitation`, `DeleteWorkspaceUsageLimit`, `EndWorkspaceBillingArrangement`, `EnrichWorkspaceCompany`, `GoBackToPreviousOnboardingStep`, `GrantWorkspaceCredits`, `ResendWorkspaceInvitation`, `RevokeWorkspaceCreditGrant`, `SendInvitations`, `SkipSyncEmailOnboardingStep`, `UpdateGettingStarted`, `UpdateTabPresence`, `UpdateUserEmail`, `UpdateWorkspace`, `UpdateWorkspaceAllowedEmbeddingOrigins`, `UpdateWorkspaceFeatureFlag`, `UpdateWorkspaceMemberSettings`, `ValidateApprovedAccessDomain`, `VerifyEmailingDomain`

### Mejl, kalender, kanaler och utskick

**Frågor (15):** `CallRecordingIdForCalendarEvent`, `GetConnectedImapSmtpCaldavAccount`, `GetMessageThreadChannel`, `GetTimelineCalendarEventsFromObjectRecord`, `GetTimelineThreadChannelsFromObjectRecord`, `GetTimelineThreadsFromObjectRecord`, `MessageSuppressions`, `MyCalendarChannels`, `MyConnectedAccounts`, `MyMessageChannels`, `MyMessageFolders`, `PreviewMessageCampaignSend`, `SearchTimelineCalendarEvents`, `SearchTimelineThreads`, `UnsubscribeTopics`

**Mutationer (23):** `CancelMessageCampaign`, `CreateCalendarEvent`, `CreateEmailGroupChannel`, `CreateUnsubscribeTopic`, `DeleteConnectedAccount`, `DeleteEmailGroupChannel`, `DeleteUnsubscribeTopic`, `DisconnectConnectedAccount`, `DuplicateMessageList`, `MarkAppChannelThreadAsRead`, `OpenDirectMessage`, `SaveImapSmtpCaldavAccount`, `SendAppChannelMessage`, `SendEmail`, `SendMessageCampaign`, `SendMessageCampaignTest`, `StartChannelSync`, `TriggerAddPeopleToMessageListJob`, `UpdateCalendarChannel`, `UpdateEmailGroupChannel`, `UpdateMessageChannel`, `UpdateMessageFolders`, `UpdateUnsubscribeTopic`

### Fakturering, krediter och användning

**Frågor (8):** `BillingPartnerCode`, `EnterpriseSubscriptionStatus`, `GetResourceCreditUsage`, `GetUsageAnalytics`, `listPlans`, `UsageQuotaDefinitions`, `UsageQuotaScopeConsumption`, `UsageQuotasWithConsumption`

**Mutationer (16):** `CancelSwitchBillingInterval`, `CancelSwitchBillingPlan`, `CancelSwitchResourceCreditPrice`, `CreateBillingPaymentMethodSetupIntent`, `CreateSubscriptionPaymentIntent`, `CreateUsageLimit`, `DeleteUsageLimit`, `EndSubscriptionTrialPeriod`, `ReleaseEnterpriseServerBinding`, `SetBillingPartnerCode`, `SetEnterpriseKey`, `SetResourceCreditSubscriptionPrice`, `SwitchBillingPlan`, `SwitchSubscriptionInterval`, `UpdateUsageLimit`, `UpdateUserCreditsFallback`

**Prenumerationer (1):** `OnEventSubscription`

### Utvecklare: API-nycklar, webhooks, realtid

**Frågor (4):** `GetApiKey`, `GetApiKeys`, `GetWebhook`, `GetWebhooks`

**Mutationer (8):** `AddQueryToEventStream`, `CreateApiKey`, `CreateWebhook`, `DeleteWebhook`, `RemoveQueryFromEventStream`, `RevokeApiKey`, `UpdateApiKey`, `UpdateWebhook`

### Serveradmin, hälsa, köer och konfiguration

**Frågor (13):** `AdminPanelRecentUsers`, `EventLogs`, `GetConfigVariablesGrouped`, `GetDatabaseConfigVariable`, `GetIndicatorHealthStatus`, `GetMaintenanceMode`, `GetQueueJobs`, `GetQueueMetrics`, `GetServerAdmins`, `GetSystemHealthStatus`, `GetUpgradeStatus`, `GetVersionInfo`, `UserLookupAdminPanel`

**Mutationer (10):** `ClearMaintenanceMode`, `CreateDatabaseConfigVariable`, `DeleteDatabaseConfigVariable`, `DeleteJobs`, `RefreshUpgradeStatus`, `RetryJobs`, `SetMaintenanceMode`, `UpdateDatabaseConfigVariable`, `UpdateLabPublicFeatureFlag`, `UpdateServerAdminAccess`

**Prenumerationer (1):** `EventLogsLive`

### Filer, sök, adress, export och berikning

**Frågor (3):** `GetAddressDetails`, `GetAutoCompleteAddress`, `Search`

**Mutationer (3):** `CompleteFileUpload`, `CreateFileUpload`, `TrackAnalytics`

**Prenumerationer (1):** `ExportRecords`

### Övrigt

**Frågor (1):** `GithubClaimAuthorizationUrl`
