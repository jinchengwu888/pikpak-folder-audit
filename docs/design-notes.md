# Design notes

Reviewed on 2026-11-06. This project combines a few general workflow ideas into an independently written, smaller utility. No third-party Skill text, helper implementation, configuration, installer, or referral code was copied into this distribution. The MIT license covers this project's original work; it does not relicense the references below.

## Decisions

- One selected folder, direct children only. A page budget limits the observation; a limit hit remains partial.
- Count unique file IDs. Conflicting observations remain visible rather than being silently overwritten.
- Add only valid, nonnegative byte counts. Unknown and zero sizes remain distinct. Folder sizes are not added to file-byte totals.
- Use reported MIME categories only. No media probing or playback claim.
- Same exact name and same positive size yield review candidates, without hashing, keeper selection, deletion advice, or a space-saving claim.
- Use an argument array for the official CLI and whitelist report fields. Raw source/signed links and unrelated account fields stay out of emitted reports. Names and metadata remain untrusted data.
- Keep registration optional and separate from audit execution. Existing accounts need no new registration; an undecided or declined referral uses explicit `--affiliate=`.

## Public references and licenses

These are evidence and conceptual references, not bundled dependencies. License observations apply to the reviewed snapshots; an unreadable or absent license is not permission to copy.

| Reference | Reviewed snapshot and license | Relevance |
| --- | --- | --- |
| [Official PikPak CLI](https://mypikpak.com/en-US/cli) and [vendor Skill archive](https://download.mypikpak.com/cli/pikpak.skill) | Official macOS ARM64 CLI v0.6.0 help checked; vendor archive read as text. No archive content redistributed. | Official executable, raw byte-size fields, one-page listings, page tokens and normal listing visibility. |
| [pikcloud/skills](https://github.com/pikcloud/skills/tree/c8a470399b3437f9efc0a7c612a016cfc86a395e) | `c8a4703`; no explicit license found in the reviewed tree. | Public command interface reference; it is documentation, not the CLI implementation. |
| [pipiguai87-alt/pikpak-skills](https://github.com/pipiguai87-alt/pikpak-skills/tree/f3caac40a811b377a8be349b9c264c940f52533b) | `f3caac4`; [MIT](https://github.com/pipiguai87-alt/pikpak-skills/blob/f3caac40a811b377a8be349b9c264c940f52533b/LICENSE). | Storage-report, dedup and media-index concepts: preserve unknown values and distinguish candidates from verified content equality. No implementation reused. |
| [Bengerthelorf/pikpaktui](https://github.com/Bengerthelorf/pikpaktui/tree/68b7a6bdf6e4abe2a049974dec2c38e736f2a25c) | `68b7a6b`; [Apache-2.0](https://github.com/Bengerthelorf/pikpaktui/blob/68b7a6bdf6e4abe2a049974dec2c38e736f2a25c/LICENSE). | Client identification and isolated synthetic checks. This is a different executable with different authentication, flags and deletion semantics. |
| [dvnhan91/pikpak-docker-guide](https://github.com/dvnhan91/pikpak-docker-guide/tree/6a1340e20845c7b11ff727b6aae7b37254fa08ff) | `6a1340e`; no explicit license found in the reviewed tree. | Explicit scope, path/ID distinctions and honest coverage. No Docker configuration or bootstrap included here. |
| [CodeCraftsfolk/oh-my-pikpak](https://github.com/CodeCraftsfolk/oh-my-pikpak/tree/2bf930993d75639666c9a22c0f1932106dd2a72e) | `2bf9309`; no explicit license found in the reviewed tree. | Preflight boundaries, structured outcomes and separation of discovery from account changes. Upload/share/search implementations are outside this audit's scope. |
| [yjl9903/AnimeGarden](https://github.com/yjl9903/AnimeGarden/tree/c83534477bfbdc27010d5115447b487b9a7846b3) | `c835344`; Skill version `2026.10.25`; [Skill AGPL-3.0](https://github.com/yjl9903/AnimeGarden/blob/c83534477bfbdc27010d5115447b487b9a7846b3/skills/animegarden/LICENSE.txt). | On-demand detail, evidence labels and ID provenance. No search service, playback-link formatter or AGPL implementation included. |

`search-videos-save-to-pikpak` is a historical name in the same CodeCraftsfolk repository, not an additional independent implementation. The name [changed](https://github.com/CodeCraftsfolk/oh-my-pikpak/commit/73b469449997f93073d3f46443b8d30057283eea) and was [restored to video-search](https://github.com/CodeCraftsfolk/oh-my-pikpak/commit/3bd4c21ffa4788650dc01c64545d6cc0a6ed8537) on 2026-09-23. A separate intervening [change removed the setup script](https://github.com/CodeCraftsfolk/oh-my-pikpak/commit/ace1d73257283e68c9539daa2bef42b54799922a). Old installation and referral behavior is not a current recommendation.

## Incomplete sources

The requested [2fun-pansou](https://www.skills.sh/site/skills.volces.com/2fun-pansou) and [pansou](https://www.skills.sh/site/skills.volces.com/pansou) directory pages and attempted public volces origin endpoints were unreadable during review. Their original package identity, current version, license and implementation remain unverified. Same-name mirrors do not resolve that uncertainty. Neither is treated as an implementation-reviewed case or a dependency.

## Verification limits

The original helper uses synthetic subprocess fixtures for listing behavior and field filtering. Official v0.6.0 help checks establish command syntax only. No real-account folder audit, third-party implementation execution, content search, cloud transfer, registration or purchase was performed for this release. Live JSON behavior, other operating systems and concurrent drive changes still require cautious interpretation.

Directory listing, installation telemetry and security badges do not establish user registrations, purchases, referral attribution, revenue, or guaranteed discovery by search engines or AI agents.
