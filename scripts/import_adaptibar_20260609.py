# -*- coding: utf-8 -*-
"""
Import 25 AdaptiBar Past Questions (report dated 6/9/2026) into mbe_cards.
Run from the project root:  python scripts/import_adaptibar_20260609.py
"""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import upsert_mbe_cards

SOURCE = "adaptibar_past_questions_20260609"

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def card(adv_id, subject, subtopic, scenario, a, b, c, d, correct):
    # Trainer option shape: "t" holds the choice text (see mbe_trap_trainer.html).
    options = [
        {"t": a, "ok": correct == "A"},
        {"t": b, "ok": correct == "B"},
        {"t": c, "ok": correct == "C"},
        {"t": d, "ok": correct == "D"},
    ]
    return {
        "adv_id": str(adv_id),
        "subject": subject,
        "subtopic": subtopic,
        "title": None,
        "scenario": scenario,
        "question": "Choose the best answer.",
        "rule_hint": None,
        "options_json": json.dumps(options),
        "plain_english": None,
        "shortcut": None,
        "source": SOURCE,
        "source_row": adv_id,
        "raw_json": None,
    }


# ---------------------------------------------------------------------------
# The 25 questions
# ---------------------------------------------------------------------------

CARDS_RAW = [

card(
    926, "Constitutional Law", "Separation of Powers",
    "A newly enacted federal statute appropriates $100 million in federal funds to support basic research by universities located in the United States. The statute provides that \"the ten best universities in the United States\" will each receive $10 million. It also provides that \"the ten best universities\" shall be \"determined by a poll of the presidents of all the universities in the nation, to be conducted by the United States Department of Education.\" In responding to that poll, each university president is required to apply the well-recognized and generally accepted standards of academic quality that are specified in the statute. The provisions of the statute are inseverable.\n\nWhich of the following statements about this statute is correct?",
    "The statute is unconstitutional, because the reliance by Congress on a poll of individuals who are not federal officials to determine the recipients of its appropriated funds is an unconstitutional delegation of legislative power.",
    "The statute is unconstitutional, because the limitation on recipients to the ten best universities is arbitrary and capricious and denies other high quality universities the equal protection of the laws.",
    "The statute is constitutional, because Congress has plenary authority to determine the objects of its spending and the methods used to achieve them, so long as they may reasonably be deemed to serve the general welfare and do not violate any prohibitory language in the Constitution.",
    "The validity of the statute is nonjusticiable, because the use by Congress of its spending power necessarily involves political considerations that must be resolved finally by those branches of the government that are closest to the political process.",
    "C",
),

card(
    2168, "Civil Procedure", "Pretrial Procedures (Simulated)",
    "On July 29, 2012, a car manufacturer filed a lawsuit against a corporation in federal court. The manufacturer mistakenly believed that the corporation was the entity responsible for producing the bolts used to secure the car tires onto the car manufacturer's cars. The manufacturer was sued after some of the cars' tires became detached during transit due to faulty bolts. The manufacturer is seeking contractual indemnification for losses stemming from these lawsuits. State law provides a five-year statute of limitations for contract claims, which starts running when a plaintiff first learns of its contract claim.\n\nThe manufacturer learned of the faulty bolts on August 1, 2007, and realized it might have a contract claim. Two weeks after filing its lawsuit, the manufacturer realized it had mistaken the corporation for a different entity that was, in fact, responsible for producing the faulty bolts.\n\nThe other entity not only knew the bolts were faulty, but was also aware of the original lawsuit against the corporation. The other entity was hoping that the manufacturer would not realize its mistake.\n\nIs the court likely to allow the manufacturer to substitute the other entity as a defendant?",
    "No, because it would be unconstitutional to allow the other entity to be made a defendant after the statute of limitations has expired.",
    "No, because the Federal Rules of Civil Procedure do not permit a party to be added to a lawsuit after the statute of limitations has expired.",
    "Yes, because the other entity knew about the manufacturer's original lawsuit and that it would have been sued but for the mistake concerning the party's identity.",
    "Yes, because the claim against the other entity arises out of the conduct, transaction, or occurrence set out in the manufacturer's original complaint.",
    "C",
),

card(
    835, "Constitutional Law", "Individual Rights",
    "The legislature of a particular state enacted a statute requiring that all law enforcement officers in that state be citizens of the United States. An alien, lawfully admitted to permanent residency five years before the enactment of this statute, sought employment as a forensic pathologist in the state coroner's office. He was denied such a job solely because he was not a citizen.\n\nThe alien thereupon brought suit in federal district court against appropriate state officials seeking to invalidate this citizenship requirement on federal constitutional grounds.\n\nThe strongest ground upon which to attack this citizenship requirement is that it",
    "constitutes an ex post facto law as to previously admitted aliens.",
    "deprives an alien of a fundamental right to employment without the due process of law guaranteed by the Fourteenth Amendment.",
    "denies an alien a right to employment in violation of the Privileges or Immunities Clause of the Fourteenth Amendment.",
    "denies an alien the equal protection of the laws guaranteed by the Fourteenth Amendment.",
    "D",
),

card(
    935, "Real Property", "Mortgages",
    "The owner of Blackacre needed money. Blackacre was fairly worth $100,000, so the owner tried to borrow $60,000 from a lender on the security of Blackacre. The lender agreed, but only if the owner would convey Blackacre to the lender outright by warranty deed, with the lender agreeing orally to reconvey to the owner once the loan was paid according to its terms. The owner agreed, conveyed Blackacre to the lender by warranty deed, and the lender paid the owner $60,000 cash. The lender promptly and properly recorded the owner's deed.\n\nNow, the owner has defaulted on repayment with $55,000 still due on the loan. The owner is still in possession.\n\nWhich of the following best states the parties' rights in Blackacre?",
    "The lender's oral agreement to reconvey is invalid under the Statute of Frauds, so the lender owns Blackacre outright.",
    "The owner, having defaulted, has no further rights in Blackacre, so the lender may obtain summary eviction.",
    "The attempted security arrangement is a creature unknown to the law, hence a nullity; the lender has only a personal right to $55,000 from the owner.",
    "The lender may bring whatever foreclosure proceeding is appropriate under the laws of the jurisdiction.",
    "D",
),

card(
    2268, "Civil Procedure", "Pretrial Procedures (Simulated)",
    "A baker owned and ran a small bakery. One evening, a fire broke out at the bakery, and the baker promptly notified his insurance company. The insurance company sent an employee to the bakery, who arrived while the fire department was still extinguishing the flames. This employee photographed the scene in detail and prepared a memorandum describing what he photographed and how he interpreted what he photographed.\n\nThe baker then brought suit in federal court against a roofer who had been working on the roof shortly before the fire broke out. The roofer declared his intention to seek to discover the photos taken and the memo written by the insurance company employee. The baker protested, citing work-product privilege. The court found that the insurance company anticipated litigation as soon as it learned of the fire.\n\nShould the court grant the roofer access to the photos and memo?",
    "Yes, the court may grant the roofer's request for the production of documents, including the photos and memo.",
    "Yes, the court may allow the roofer to serve the baker with interrogatories inquiring the photographs and other memorialization prepared by the insurance company.",
    "No, because the roofer must first obtain an order of the court allowing him to have access to this work product material.",
    "No, because the roofer had the opportunity to send his own investigator to the site of the fire.",
    "C",
),

card(
    836, "Real Property", "Rights in Land",
    "An owner owned 80 acres of land, fronting on a town road. Two years ago, the owner sold to a buyer the back 40 acres. The 40 acres sold to the buyer did not adjoin any public road. The owner's deed to the buyer expressly granted a right-of-way over a specified strip of the owner's retained 40 acres, so the buyer could reach the town road. The deed was promptly and properly recorded.\n\nLast year, the buyer conveyed the back 40 acres to a doctor. They had discussed the right-of-way over the owner's land to the road, but the buyer's deed to the doctor made no mention of it. The doctor began to use the right-of-way as the buyer had, but the owner sued to enjoin such use by the doctor.\n\nThe court should decide for",
    "the doctor, because he has an easement by implication.",
    "the doctor, because the easement appurtenant passed to him as a result of the buyer's deed to him.",
    "the owner, because the buyer's easement in gross was not transferable.",
    "the owner, because the buyer's deed failed expressly to transfer the right-of-way to the doctor.",
    "B",
),

card(
    886, "Evidence", "Presentation of Evidence",
    "A plaintiff sued a defendant for dissolution of their year-long partnership. One issue concerned the amount of money the plaintiff had received in cash. It was customary for the defendant to give the plaintiff money from the cash register as the plaintiff needed it for personal expenses. The plaintiff testified that, as he received money, he jotted down the amounts in the partnership ledger. Although the defendant had access to the ledger, he made no changes in it. The defendant seeks to testify to his memory of much larger amounts he had given the plaintiff.\n\nThe defendant's testimony is",
    "admissible, because it is based on the defendant's firsthand knowledge.",
    "admissible, because the ledger entries offered by a party opponent opened the door.",
    "inadmissible, because the ledger is the best evidence of the amounts the plaintiff received.",
    "inadmissible, because the defendant's failure to challenge the accuracy of the ledger constituted an adoptive admission.",
    "A",
),

card(
    1291, "Criminal Law", "Inchoate Crimes",
    "Four men are being tried for conspiracy to commit a series of bank robberies. Nine successful bank robberies took place during the period of the charged conspiracy. Because the robbers wore masks and gloves and stole the bank surveillance tapes, no witnesses have been able to directly identify the robbers. Some circumstantial evidence ties each of the men to the overall conspiracy. During cross-examination, a prosecution witness testified that one of the men was in jail on other charges during the last six robberies. That man's lawyer has moved for a judgment of acquittal at the close of the government's case.\n\nShould the motion be granted?",
    "No, because a conspirator is not required to agree to all of the objectives of the conspiracy.",
    "No, because a conspirator need not be present at the commission of each crime conspired upon.",
    "Yes, provided that the man has complied with the rule requiring pretrial notice of alibi.",
    "Yes, regardless of compliance with the alibi rule, because the government is bound by exculpatory evidence elicited during its case-in-chief.",
    "B",
),

card(
    1172, "Real Property", "Mortgages",
    "The owner in fee simple of Orchardacres, mortgaged Orchardacres to a lender to secure the payment of a loan the lender made to the owner. The loan was due at the end of the growing season of the year in which it was made. The owner maintained and operated an orchard on the land, which was his sole source of income. Halfway through the growing season, the owner experienced severe health and personal problems and, as a result, left the state; his whereabouts were unknown. The lender learned that no one was responsible for the cultivation and care of the orchard on Orchardacres. The lender undertook to provide, through employees, the care of the orchard and the harvest for the remainder of the growing season. The net profits were applied to the debt secured by the mortgage on Orchardacres.\n\nDuring the course of the harvest, a business invitee was injured by reason of a fault in the equipment used. Under applicable tort case law, the owner of the premises would be liable for the business invitee's injuries. The business invitee brought an appropriate action against the lender to recover damages for the injuries suffered, relying on this aspect of tort law.\n\nIn such lawsuit, judgment should be for",
    "the lender, because the state is not a title theory state, so a mortgagee has no title interest but only a lien.",
    "the business invitee, because the lender was a mortgagee in possession.",
    "the lender, because she acted as agent of the owner only to preserve her security interest.",
    "the business invitee, because the mortgage did not expressly provide for the lender taking possession in the event of danger to her security interest.",
    "B",
),

card(
    2118, "Civil Procedure", "Pretrial Procedures",
    "A man asked his attorney whether he had a legal basis to challenge a rate increase proposed by his electric utility company. The attorney said that he did and filed a federal action seeking a declaratory judgment that the proposed increase would violate federal law.\n\nSoon thereafter, the court issued an order requiring the man and his attorney to show cause why they should not be sanctioned under Rule 11 and required to pay a monetary penalty to the court for filing a frivolous complaint. The order cited several recent judicial decisions holding that rate increases such as the one proposed do not violate federal law.\n\nMay the court impose this monetary sanction on the man?",
    "No, because the court cannot impose a monetary sanction under Rule 11 without a motion seeking such a sanction.",
    "No, because the man is represented by an attorney.",
    "Yes, because the action is not warranted by existing law.",
    "Yes, because the court issued a show-cause order before imposing any sanction.",
    "B",
),

card(
    1115, "Constitutional Law", "Relations Between Federal and State Governments",
    "A state imposes a tax on the \"income\" of each of its residents. As defined in the taxing statute, \"income\" includes the fair rental value of the use of any automobile provided by the taxpayer's employer for personal use. The federal government supplies automobiles to some of its employees who are residents of the state so that they may perform their jobs properly. A federal government employee supplied with an automobile for this purpose may also use it for the employee's own personal business.\n\nAssume there is no federal legislation on this subject.\n\nMay the state collect this tax on the fair rental value of the personal use of the automobiles furnished by the federal government to these employees?",
    "No, because such a tax would be a tax on the United States.",
    "No, because such a tax would be a tax upon activities performed on behalf of the United States, since the automobiles are primarily used by these federal employees in the discharge of their official duties.",
    "Yes, because the tax is imposed on the employees rather than on the United States, and the tax does not discriminate against persons who are employed by the United States.",
    "Yes, because an exemption from such state taxes for federal employees would be a denial to others of the equal protection of the laws.",
    "C",
),

card(
    1082, "Criminal Law", "Homicide",
    "At 11:00 p.m., a couple was accosted in the entrance to their apartment building by the defendant, who was armed as well as masked. The defendant ordered the couple to take him into their apartment. After they entered the apartment, the defendant forced the woman to bind and gag her husband and then to open a safe which contained a diamond necklace. The defendant then tied her up and fled with the necklace. He was apprehended by apartment building security guards. Before the guards could return to the apartment, but after the defendant was arrested, the husband, straining to free himself, suffered a massive heart attack and died.\n\nThe defendant is guilty of",
    "burglary, robbery, and murder.",
    "robbery and murder only.",
    "burglary and robbery only.",
    "robbery only.",
    "A",
),

card(
    2132, "Civil Procedure", "Jurisdiction and Venue (Simulated)",
    "A pedestrian from State A sued a motorcyclist from State B. The pedestrian properly filed suit in a state court located in the Eastern District of State A and sought $100,000 in damages for the tortious injuries caused by the motorcyclist's allegedly negligent acts in the Western District of State A.\n\nThe motorcyclist filed a notice of removal in the federal court for the Eastern District of State A, which geographically embraces the location of where the action was originally filed.\n\nIs removal proper?",
    "Yes, because the requirements of complete diversity are satisfied.",
    "Yes, because the lawsuit was filed in state court in the Eastern District of State A.",
    "No, because the motorcyclist is a citizen of State B.",
    "No, because the accident occurred in the Western District of State A.",
    "B",
),

card(
    2240, "Civil Procedure", "Jurisdiction and Venue (Simulated)",
    "An investor from State A sued a State A company in State A court, asserting two claims: (i) a violation of federal securities laws, over which state and federal courts have concurrent subject-matter jurisdiction; and (ii) fraud under State A law. The company filed a notice of removal in the local federal district court. Several months later, after seeking the advice of counsel, the investor decided to voluntarily dismiss his federal claim and moved to remand the case to state court.\n\nMay the court grant the investor's motion to remand?",
    "Yes, because if the federal court lacks subject-matter jurisdiction at any time before final judgment, it may use its discretion to remand.",
    "Yes, because the federal court has dismissed all claims over which there existed an independent basis of jurisdiction, and the case must be remanded to state court.",
    "No, because the federal court still has subject-matter jurisdiction, even after dismissal of the federal claim, and is therefore obligated to hear the case.",
    "No, because the motion to remand was made more than 30 days after the filing of the notice of removal and is therefore untimely.",
    "B",
),

card(
    1556, "Criminal Law", "Homicide",
    "A wife decided to kill her husband because she was tired of his infidelity. She managed to obtain some cyanide, a deadly poison. One evening, she poured wine laced with the cyanide into a glass, handed it to her husband, and proposed a loving toast. The husband was so pleased with the toast that he set the glass of wine down on a table, grabbed his wife, and kissed her passionately. After the kiss, the wife changed her mind about killing the husband. She hid the glass of wine behind a lamp on the table, planning to leave it for the maid to clean up. The husband did not drink the wine.\n\nThe maid found the glass of wine while cleaning the next day. Rather than throw the wine away, the maid drank it. Shortly thereafter, she fell into a coma and died from cyanide poisoning.\n\nIn a common law jurisdiction, of what crime(s), if any, could the wife be found guilty?",
    "Attempted murder of the husband and murder or manslaughter of the maid.",
    "Only attempted murder of the husband.",
    "Only murder or manslaughter of the maid.",
    "No crime.",
    "A",
),

card(
    1393, "Contracts", "Performance, Breach, and Discharge",
    "A seller and a buyer entered into a written agreement providing that the seller was to deliver 1,000 cases of candy bars to the buyer during the months of May and June. Under the agreement, the buyer was obligated to make a selection by March 1 of the quantities of the various candy bars to be delivered under the contract. The buyer did not make the selection by March 1, and on March 2, the seller notified the buyer that because of the buyer's failure to select, the seller would not deliver the candy bars. The seller had all of the necessary candy bars on hand on March 1 and made no additional sales or purchases on March 1 or March 2. On March 2, after receiving the seller's notice that it would not perform, the buyer notified the seller of its selection and insisted that the seller perform. The seller refused.\n\nIf the buyer sues the seller for breach of contract, is the buyer likely to prevail?",
    "No, because a contract did not exist until the buyer selected the specific candy bars, and the seller withdrew its offer before selection.",
    "No, because the buyer's selection of the candy bars by March 1 was an express condition to the seller's duty to perform.",
    "Yes, because the delay of one day in making the selection did not have a material effect on the seller.",
    "Yes, because upon the buyer's failure to make a selection by March 1, the seller had a duty to make a reasonable selection.",
    "C",
),

card(
    1416, "Criminal Law", "Constitutional Protection of Accused Persons",
    "A store owner whose jewelry store had recently been robbed was shown by a police detective a photograph of the defendant, who previously had committed other similar crimes. The store owner examined the photograph and then asked the detective whether the police believed that the man pictured was the robber. After the detective said, \"We're pretty sure,\" the store owner stated that the man in the photograph was the one who had robbed her.\n\nThe defendant was indicted for the robbery. His counsel moved to suppress any trial testimony by the store owner identifying the defendant as the robber.\n\nShould the court grant the motion and suppress the store owner's trial testimony identifying the defendant as the robber?",
    "No, because suppression of in-court testimony is not a proper remedy, even though the out-of-court identification was improper.",
    "No, because the out-of-court identification was not improper.",
    "Yes, because the improper out-of-court identification has necessarily tainted any in-court identification.",
    "Yes, unless the prosecution demonstrates that the in-court identification is reliable.",
    "D",
),

card(
    1244, "Evidence", "Hearsay and Circumstances of Its Admissibility",
    "A homeowner sued a plumber for damages resulting from the plumber's allegedly faulty installation of water pipes in her basement, which caused flooding. At trial, the homeowner is prepared to testify that when she first detected the flooding, she turned off the water and called the plumber at his emergency number for help and that the plumber responded, \"I'll come by tomorrow and redo the installation for free.\"\n\nIs the homeowner's testimony regarding the plumber's response admissible?",
    "No, because the statement was an offer in compromise.",
    "No, because it is hearsay not within any exception.",
    "Yes, as a subsequent remedial measure.",
    "Yes, as evidence of the plumber's fault.",
    "D",
),

card(
    1345, "Contracts", "Remedies",
    "On May 1, a seller and a buyer entered into a written contract, signed by both parties, for the sale of a tract of land for $100,000. Delivery of the deed and payment of the purchase price were scheduled for July 1. On June 1, the buyer received a letter from the seller repudiating the contract. On June 5, the buyer bought a second tract of land at a higher price as a substitute for the first tract. On June 10, the seller communicated a retraction of the repudiation to the buyer.\n\nThe buyer did not tender the purchase price for the first tract on July 1 but subsequently sued the seller for breach of contract.\n\nWill the buyer likely prevail?",
    "No, because the seller retracted the repudiation prior to the agreed time for performance.",
    "No, because the buyer's tender of the purchase price on July 1 was a constructive condition to the seller's duty to tender a conveyance.",
    "Yes, because the seller's repudiation was not retractable after it was communicated to the buyer.",
    "Yes, because the buyer bought the second tract as a substitute for the first tract prior to the seller's retraction.",
    "D",
),

card(
    834, "Torts", "Intentional Torts",
    "A man owned a shotgun that he used for hunting. The man knew that his old friend had become involved with a violent gang that recently had a shoot-out with a rival gang. The man, who was going to a farm to hunt quail, placed his loaded shotgun on the back seat of his car. On his way to the farm, the man picked up his old friend to give him a ride to someone's house. After dropping off his old friend at the house, the man proceeded to the farm, where he discovered that his shotgun was missing from his car. The old friend had taken the shotgun and, later in the day, the old friend used it to shoot a member of the rival gang. The gang member was severely injured.\n\nThe gang member recovered a judgment for his damages against the man, as well as the old friend, on the ground that the man was negligent in allowing his old friend to obtain possession of the gun, and was therefore liable jointly and severally with the old friend for the gang member's damages. The jurisdiction has a statute that allows contribution based upon proportionate fault and adheres to the traditional common-law rules on indemnity.\n\nIf the man fully satisfies the judgment, he then will have a right to recover from the old friend",
    "indemnity for the full amount of the judgment, because the old friend was an intentional tortfeasor.",
    "contribution only, based on comparative fault, because the man himself was negligent.",
    "one-half of the amount of the judgment.",
    "nothing, because the man's negligence was a substantial proximate cause of the shooting.",
    "A",
),

card(
    1173, "Torts", "Other Torts",
    "A well-known movie star was drinking Vineyard wine at a nightclub. A bottle of the Vineyard wine, with its label plainly showing, was on the table in front of the actor. An amateur photographer asked the actor if he could take his picture and the actor said, \"Yes.\" Subsequently, the photographer sold the photo to Vineyard. Vineyard, without the actor's consent, used the photo in a wine advertisement in a nationally circulated magazine. The caption below the photo stated that the actor \"enjoys his Vineyard wine.\"\n\nIf the actor sues Vineyard to recover damages as a result of Vineyard's use of the photograph, will the actor prevail?",
    "No, because the actor consented to being photographed.",
    "No, because the actor is a public figure.",
    "Yes, because Vineyard made commercial use of the photograph.",
    "Yes, unless the actor did, in fact, enjoy his Vineyard wine.",
    "C",
),

card(
    991, "Real Property", "Titles",
    "A doctor owned Blackacre, which was improved with a dwelling. Her neighbor owned Whiteacre, an adjoining unimproved lot suitable for constructing a dwelling. The neighbor executed and delivered a deed granting to the doctor an easement over the westerly 15 feet of Whiteacre for convenient ingress and egress to a public street, although the doctor's lot did abut another public street. The doctor did not then record the neighbor's deed. After the doctor constructed and started using a driveway within the described 15-foot string in a clearly visible manner, the neighbor borrowed $10,000 cash from a bank and gave the bank a mortgage on Whiteacre. The mortgage was promptly and properly recorded. The doctor then recorded the neighbor's deed granting the easement. The neighbor subsequently defaulted on her loan payments to the bank.\n\nThe recording act of the jurisdiction provides: \"No conveyance or mortgage of real property shall be good against subsequent purchasers for value and without notice unless the same be recorded according to law.\"\n\nIn an appropriate foreclosure action as to Whiteacre, brought against the doctor and the neighbor, the bank seeks, among other things, to have the doctor's easement declared subordinate to the bank's mortgage, so that the easement will be terminated by completion of the foreclosure.\n\nIf the doctor's easement is NOT terminated, it will be because",
    "the recording of the deed granting the easement prior to the foreclosure action protects the doctor's rights.",
    "the easement provides access from Blackacre to a public street.",
    "the doctor's easement is appurtenant to Blackacre and thus cannot be separated from Blackacre.",
    "visible use of the easement by the doctor put the bank on notice of the easement.",
    "D",
),

card(
    1265, "Evidence", "Hearsay and Circumstances of Its Admissibility",
    "In a civil action for misrepresentation in the sale of real estate, the parties contested whether the defendant was licensed by the State Board of Realtors, a public agency established by statute to license real estate brokers. The defendant testified that she was licensed. On rebuttal, the plaintiff has offered a certification, bearing the seal of the secretary of the State Board of Realtors. The certification states that the secretary conducted a thorough search of the agency's records and all relevant databases, and that this search uncovered no record of a license ever having been issued to the defendant. The certification is signed by the secretary.\n\nIs the certification that there is no record of a license having been issued to the defendant admissible?",
    "No, because it is hearsay not within any exception.",
    "No, because the writing was not properly authenticated.",
    "Yes, for the limited purpose of impeaching the defendant.",
    "Yes, to prove the nonexistence of a public record.",
    "D",
),

card(
    843, "Contracts", "Defenses to Enforceability",
    "A son, who knew nothing about horses, inherited a thoroughbred colt whose disagreeable behavior made him a pest around the barn. The son sold the colt for $1,500 to an experienced racehorse-trainer who knew of the son's ignorance about horses. At the time of the sale, the son said to the trainer, \"I hate to say it, but this horse is bad-tempered and nothing special.\"\n\nAssume that soon after the sale, the horse won three races and earned $400,000 for the trainer.\n\nWhich of the following additional facts, if established by the son, would best support his chance of obtaining rescission of the sale to the trainer?",
    "The son did not know until after the sale that the purchaser was an experienced racehorse-trainer.",
    "At a pre-sale exercise session of which the trainer knew that the son was not aware, the trainer clocked the horse in record-setting time, far surpassing any previous performance.",
    "The horse was the only thoroughbred that the son owned, and the son did not know how to evaluate young and untested racehorses.",
    "At the time of the sale, the son was angry and upset over an incident in which the horse had reared and thrown a rider.",
    "B",
),

card(
    1174, "Evidence", "Hearsay and Circumstances of Its Admissibility",
    "At a defendant's trial for sale of drugs, the government called a witness to testify, but the witness refused to answer any questions about the defendant and was held in contempt of court. The government then calls a police officer to testify that, when the witness was arrested for possession of drugs and offered leniency if he would identify his source, the witness had named the defendant as his source.\n\nThe testimony offered concerning the witness's identification of the defendant is",
    "admissible as a prior consistent statement by a witness.",
    "admissible as an identification of the defendant by a witness after having perceived him.",
    "inadmissible, because it is hearsay not within any exception.",
    "inadmissible, because the witness was not confronted with the statement while on the stand.",
    "C",
),

]  # end CARDS_RAW


# ---------------------------------------------------------------------------
# Generate card_uid using same logic as mbe_import_services._card_uid
# ---------------------------------------------------------------------------

import hashlib

def _normalize_for_uid(text):
    if not text:
        return ""
    import re
    text = str(text).lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text

def _card_uid(subject, subtopic, title, scenario, question, correct_text):
    fingerprint = "||".join([
        _normalize_for_uid(subject),
        _normalize_for_uid(subtopic),
        _normalize_for_uid(title or question),
        _normalize_for_uid(scenario),
        _normalize_for_uid(correct_text),
    ])
    return hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()[:24]


def build_cards(raw_cards):
    result = []
    for c in raw_cards:
        options = json.loads(c["options_json"])
        correct_text = next((o.get("t") or o.get("text", "") for o in options if o["ok"]), "")
        uid = _card_uid(
            c["subject"], c["subtopic"], c["title"],
            c["scenario"], c["question"], correct_text,
        )
        result.append({**c, "card_uid": uid})
    return result


if __name__ == "__main__":
    cards = build_cards(CARDS_RAW)
    result = upsert_mbe_cards(cards)
    print(f"Done: inserted={result['inserted']}  updated={result['updated']}  skipped={result['skipped']}")
    if result.get("skipped_builtin"):
        print(f"  skipped_builtin={result['skipped_builtin']}")
