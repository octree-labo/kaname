import { DocumentNewPage } from "@/components/document/DocumentNewPage";
import { purchasesModule } from "@/lib/documentModules";

export default function Page() {
  return <DocumentNewPage config={purchasesModule} />;
}
